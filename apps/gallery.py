import os
import time
import socket
import urllib.parse
import urllib.request
import http.server
import socketserver
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QGridLayout, QStackedWidget, QScroller, QDialog, QProgressBar
)

# =================================================================
# BACKGROUND WEB SERVER & SIGNALS
# =================================================================
class UploadSignals(QObject):
    client_connected = pyqtSignal()
    client_disconnected = pyqtSignal()
    upload_started = pyqtSignal()
    upload_progress = pyqtSignal(int)
    upload_finished = pyqtSignal(str)


class UploadHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Completely silences terminal spam from the HTTP Server

    def do_GET(self):
        if self.path == '/ping':
            if hasattr(self.server, 'qt_signals'):
                self.server.last_ping = time.time()
                if not getattr(self.server, 'is_connected', False):
                    self.server.is_connected = True
                    self.server.qt_signals.client_connected.emit()
            self.send_response(200)
            self.end_headers()
            return
            
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """<!DOCTYPE html>
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0C0C0E; color: white; text-align: center; padding: 40px 20px; }
                input[type="file"] { display: none; }
                .btn { background: #5A8DEF; padding: 18px 40px; border-radius: 12px; color: white; border: none; font-size: 20px; margin: 20px; display: inline-block; cursor: pointer; font-weight: bold; box-shadow: 0 4px 15px rgba(90, 141, 239, 0.4); }
                .btn:active { background: #4A7DDF; }
                #progress { color: #AAAAAA; margin-top: 30px; font-size: 18px; }
            </style>
            </head><body>
            <h2 style="font-size: 28px; margin-bottom: 10px;">Upload Photos</h2>
            <p style="color: #888888; font-size: 16px; line-height: 1.5; margin-bottom: 40px;">Select images from your device to beam them directly to the Kiosk OS.</p>
            <label for="fileInput" class="btn">Select Images</label>
            <input type="file" id="fileInput" multiple accept="image/*" onchange="upload()">
            <div id="progress"></div>
            <script>
                // Pings the Kiosk OS constantly so it knows the phone is still connected
                setInterval(() => fetch('/ping').catch(()=>{}), 1000);
                
                async function upload() {
                    const files = document.getElementById('fileInput').files;
                    let div = document.getElementById('progress');
                    for (let i=0; i<files.length; i++) {
                        const file = files[i];
                        div.innerText = `Sending file ${i+1} of ${files.length}...`;
                        await fetch('/upload?filename=' + encodeURIComponent(file.name), {
                            method: 'POST',
                            body: file,
                            headers: {'Content-Type': 'application/octet-stream'}
                        });
                    }
                    div.innerHTML = "<span style='color: #1ED760;'>All files sent successfully!</span>";
                    setTimeout(() => div.innerText="", 4000);
                    document.getElementById('fileInput').value = '';
                }
            </script>
            </body></html>"""
            self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        if self.path.startswith('/upload'):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            filename = qs.get('filename', ['image.jpg'])[0]
            content_length = int(self.headers.get('Content-Length', 0))
            
            os.makedirs("photos", exist_ok=True)
            base, ext = os.path.splitext(filename)
            save_path = os.path.join("photos", filename)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join("photos", f"{base}_{counter}{ext}")
                counter += 1

            if hasattr(self.server, 'qt_signals'):
                self.server.qt_signals.upload_started.emit()
            
            bytes_read = 0
            with open(save_path, 'wb') as f:
                while bytes_read < content_length:
                    chunk_size = min(65536, content_length - bytes_read)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk: break
                    f.write(chunk)
                    bytes_read += len(chunk)
                    progress = int((bytes_read / content_length) * 100)
                    if hasattr(self.server, 'qt_signals'):
                        self.server.qt_signals.upload_progress.emit(progress)
            
            if hasattr(self.server, 'qt_signals'):
                self.server.qt_signals.upload_finished.emit(save_path)
            
            self.send_response(200)
            self.end_headers()


class UploadServerThread(QThread):
    def __init__(self, signals, port=8080):
        super().__init__()
        self.signals = signals
        self.port = port
        self.server = None

    def run(self):
        socketserver.TCPServer.allow_reuse_address = True
        class TCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer): pass
        try:
            self.server = TCPServer(('0.0.0.0', self.port), UploadHandler)
            self.server.qt_signals = self.signals
            self.server.last_ping = 0
            self.server.is_connected = False
            self.server.serve_forever()
        except Exception as e:
            print(f"Gallery Server error: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class QRFetchThread(QThread):
    on_qr_ready = pyqtSignal(QPixmap)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'KioskOS'})
            with urllib.request.urlopen(req, timeout=5) as r:
                pix = QPixmap()
                pix.loadFromData(r.read())
                self.on_qr_ready.emit(pix)
        except Exception:
            pass


# =================================================================
# UI COMPONENTS
# =================================================================
class ModernDialog(QDialog):
    """A sleek, Android/One UI style popup dialog."""
    def __init__(self, parent, title, message, accept_text="OK", cancel_text="Cancel"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(460, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bg_frame = QFrame(self)
        bg_frame.setStyleSheet("background-color: #22222B; border-radius: 20px; border: 1px solid #33333F;")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(30, 30, 30, 25)
        bg_layout.setSpacing(15)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Google Sans", 20, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")

        lbl_msg = QLabel(message)
        lbl_msg.setFont(QFont("Google Sans", 15))
        lbl_msg.setStyleSheet("color: #CCCCCC; border: none;")
        lbl_msg.setWordWrap(True)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        bg_layout.addWidget(lbl_title)
        bg_layout.addWidget(lbl_msg)
        bg_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()

        if cancel_text:
            btn_cancel = QPushButton(cancel_text)
            btn_cancel.setFixedHeight(45)
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet("""
                QPushButton { background: transparent; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; padding: 0 20px; }
                QPushButton:hover { background-color: rgba(255,255,255,10); }
            """)
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)

        btn_accept = QPushButton(accept_text)
        btn_accept.setFixedHeight(45)
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.setStyleSheet("""
            QPushButton { background-color: #E24A4A; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; border: none; padding: 0 25px; }
            QPushButton:hover { background-color: #C0392B; }
        """)
        btn_accept.clicked.connect(self.accept)
        btn_layout.addWidget(btn_accept)

        bg_layout.addLayout(btn_layout)
        layout.addWidget(bg_frame)


class ImageButton(QPushButton):
    def __init__(self, img_path, click_cb):
        super().__init__()
        self.img_path = img_path
        self.setFixedSize(200, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton { background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; }
            QPushButton:hover { border-color: #5A8DEF; }
        """)
        
        pix = QPixmap(img_path)
        if not pix.isNull():
            side = min(pix.width(), pix.height())
            x = (pix.width() - side) // 2
            y = (pix.height() - side) // 2
            cropped = pix.copy(x, y, side, side)
            
            scaled_pix = cropped.scaled(196, 196, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            rounded = QPixmap(196, 196)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, 196, 196, 11, 11)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled_pix)
            painter.end()

            self.setIcon(QIcon(rounded))
            self.setIconSize(QSize(196, 196))
            
        self.clicked.connect(lambda: click_cb(img_path))


class GalleryPage(QWidget):
    def __init__(self, on_close=None):
        super().__init__()
        self.on_close = on_close
        self.setStyleSheet("background-color: #0C0C0E; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # --- 1. Grid View ---
        self.grid_page = QWidget()
        grid_layout = QVBoxLayout(self.grid_page)
        grid_layout.setContentsMargins(40, 25, 40, 30)
        
        header = QHBoxLayout()
        title = QLabel("Gallery")
        title.setFont(QFont("Google Sans", 28, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Connection Status Label
        self.lbl_connected = QLabel("📱 Device connected.")
        self.lbl_connected.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        self.lbl_connected.setStyleSheet("color: #1ED760;")
        self.lbl_connected.hide()
        header.addWidget(self.lbl_connected)
        header.addSpacing(20)
        
        # Upload Button Setup
        self.btn_upload = QPushButton("  Upload")
        
        # Programmatically draw the upload icon
        icon_pix = QPixmap(24, 24)
        icon_pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("white"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(12, 18, 12, 4)
        painter.drawLine(12, 4, 6, 10)
        painter.drawLine(12, 4, 18, 10)
        painter.drawLine(4, 22, 20, 22)
        painter.end()
        
        self.btn_upload.setIcon(QIcon(icon_pix))
        self.btn_upload.setIconSize(QSize(20, 20))
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; padding: 0px 20px; font-weight: bold; font-size: 16px; border: none; height: 45px; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        self.btn_upload.clicked.connect(self.show_qr_code)
        header.addWidget(self.btn_upload)
        
        if self.on_close:
            header.addSpacing(15)
            btn_close = QPushButton("✕")
            btn_close.setFixedSize(45, 45)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
            btn_close.setStyleSheet("""
                QPushButton { background-color: #2C2C35; color: #AAAAAA; border-radius: 22px; border: none; }
                QPushButton:hover { background-color: #E24A4A; color: white; }
            """)
            btn_close.clicked.connect(self.shutdown_and_close)
            header.addWidget(btn_close)
            
        grid_layout.addLayout(header)
        
        # Gradient Loading Bar
        self.upload_progress = QProgressBar()
        self.upload_progress.setTextVisible(False)
        self.upload_progress.setFixedHeight(6)
        self.upload_progress.setStyleSheet("""
            QProgressBar { background: #1C1C22; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5A8DEF, stop:1 #9B59B6); border-radius: 3px; }
        """)
        self.upload_progress.hide()
        grid_layout.addWidget(self.upload_progress)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_container)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setSpacing(25)
        
        self.scroll.setWidget(self.grid_container)
        grid_layout.addWidget(self.scroll)
        self.stack.addWidget(self.grid_page)
        
        # --- 2. Fullscreen Viewer ---
        self.fs_page = QWidget()
        self.fs_page.setStyleSheet("background-color: #000000;")
        fs_layout = QVBoxLayout(self.fs_page)
        fs_layout.setContentsMargins(20, 20, 20, 20)
        
        fs_header = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setFixedSize(110, 45)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton { background-color: rgba(255,255,255,20); color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; }
            QPushButton:hover { background-color: rgba(255,255,255,40); }
        """)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.btn_del = QPushButton("🗑️ Delete")
        self.btn_del.setFixedSize(110, 45)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setStyleSheet("""
            QPushButton { background-color: rgba(226, 74, 74, 40); color: #E24A4A; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; }
            QPushButton:hover { background-color: #E24A4A; color: white; }
        """)
        self.btn_del.clicked.connect(self.delete_current_image)
        
        fs_header.addWidget(self.btn_back)
        fs_header.addStretch()
        fs_header.addWidget(self.btn_del)
        
        self.lbl_fs_img = QLabel()
        self.lbl_fs_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        fs_layout.addLayout(fs_header)
        fs_layout.addWidget(self.lbl_fs_img, stretch=1)
        self.stack.addWidget(self.fs_page)

        # --- 3. QR Code Page ---
        self.qr_page = QWidget()
        qr_layout = QVBoxLayout(self.qr_page)
        qr_layout.setContentsMargins(40, 30, 40, 30)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_qr_back = QPushButton("← Back")
        btn_qr_back.setFixedSize(110, 45)
        btn_qr_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_qr_back.setStyleSheet("""
            QPushButton { background-color: #2C2C35; color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; }
            QPushButton:hover { background-color: #383845; }
        """)
        btn_qr_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setFixedSize(250, 250)
        self.lbl_qr.setStyleSheet("background-color: #1C1C22; border-radius: 16px;")
        
        lbl_qr_inst = QLabel("Scan this code with your phone to upload images.")
        lbl_qr_inst.setFont(QFont("Google Sans", 18))
        lbl_qr_inst.setStyleSheet("color: #AAAAAA;")
        lbl_qr_inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        qr_layout.addWidget(btn_qr_back, alignment=Qt.AlignmentFlag.AlignLeft)
        qr_layout.addStretch()
        qr_layout.addWidget(self.lbl_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        qr_layout.addSpacing(20)
        qr_layout.addWidget(lbl_qr_inst, alignment=Qt.AlignmentFlag.AlignCenter)
        qr_layout.addStretch()
        self.stack.addWidget(self.qr_page)
        
        self.current_img_path = None
        self.load_images()

        # Web Server Bootup
        self.upload_signals = UploadSignals()
        self.upload_signals.client_connected.connect(self.on_client_connected)
        self.upload_signals.client_disconnected.connect(self.on_client_disconnected)
        self.upload_signals.upload_started.connect(self.on_upload_started)
        self.upload_signals.upload_progress.connect(self.on_upload_progress)
        self.upload_signals.upload_finished.connect(self.on_upload_finished)
        
        self.server_thread = UploadServerThread(self.upload_signals)
        self.server_thread.start()
        
        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self.check_connection_timeout)
        self.ping_timer.start(2000)

    # Server Event Handlers
    def on_client_connected(self):
        self.lbl_connected.show()
        if self.stack.currentIndex() == 2:
            self.stack.setCurrentIndex(0)
            
    def on_client_disconnected(self):
        self.lbl_connected.hide()
        
    def on_upload_started(self):
        self.upload_progress.setValue(0)
        self.upload_progress.show()
        
    def on_upload_progress(self, val):
        self.upload_progress.setValue(val)
        
    def on_upload_finished(self, path):
        self.upload_progress.hide()
        self.load_images()
        
    def check_connection_timeout(self):
        if hasattr(self, 'server_thread') and self.server_thread.server:
            srv = self.server_thread.server
            if getattr(srv, 'is_connected', False):
                if time.time() - srv.last_ping > 2.5:
                    srv.is_connected = False
                    self.upload_signals.client_disconnected.emit()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.254.254.254', 1))
            return s.getsockname()[0]
        except Exception: return '127.0.0.1'

    def show_qr_code(self):
        ip = self.get_local_ip()
        url = f"http://{ip}:8080"
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(url)}&bgcolor=1C1C22&color=FFFFFF"
        
        self.lbl_qr.setText("Generating QR...")
        self.lbl_qr.setStyleSheet("background-color: #1C1C22; color: #5A8DEF; font-size: 16px; border-radius: 16px;")
        
        self.qr_thread = QRFetchThread(api_url)
        self.qr_thread.on_qr_ready.connect(self.set_qr_image)
        self.qr_thread.start()
        
        self.stack.setCurrentIndex(2)

    def set_qr_image(self, pix):
        self.lbl_qr.setPixmap(pix)
        self.lbl_qr.setStyleSheet("background-color: transparent;")

    def load_images(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.deleteLater()
            
        directories = ["screenshots", "photos", "Pictures"]
        image_files = []
        
        for d in directories:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_files.append(os.path.join(d, f))
                        
        image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        if not image_files:
            lbl_empty = QLabel("No images found.\nTake a screenshot by pressing '\\' (Backslash).")
            lbl_empty.setFont(QFont("Google Sans", 18))
            lbl_empty.setStyleSheet("color: #666670;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(lbl_empty, 0, 0)
            return
            
        cols = 4
        for i, path in enumerate(image_files):
            btn = ImageButton(path, self.open_image)
            self.grid.addWidget(btn, i // cols, i % cols)
            
    def open_image(self, path):
        self.current_img_path = path
        pix = QPixmap(path)
        if not pix.isNull():
            scaled = pix.scaled(984, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_fs_img.setPixmap(scaled)
        self.stack.setCurrentIndex(1)
        
    def delete_current_image(self):
        if self.current_img_path and os.path.exists(self.current_img_path):
            dialog = ModernDialog(self, "Delete Image", "Are you sure you want to permanently delete this image?", "Delete")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    os.remove(self.current_img_path)
                    self.load_images()
                    self.stack.setCurrentIndex(0)
                except Exception as e:
                    print(f"Failed to delete image: {e}")

    def shutdown_and_close(self):
        if hasattr(self, 'server_thread'):
            self.server_thread.stop()
            self.server_thread.wait()
        if self.on_close:
            self.on_close()