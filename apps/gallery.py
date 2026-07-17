import os
import time
import socket
import shutil
import urllib.parse
import urllib.request
import http.server
import socketserver
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QObject, QPoint, QRect, QRectF, QPointF
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QPainterPath, QPen, QColor, QTransform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QGridLayout, QStackedWidget, QScroller, QDialog, QProgressBar, QLineEdit, QSlider
)

# =================================================================
# BACKGROUND WEB SERVER & SIGNALS (PORT CHANGED TO 52634)
# =================================================================
SERVER_PORT = 52634

class UploadSignals(QObject):
    client_connected = pyqtSignal()
    client_disconnected = pyqtSignal()
    upload_started = pyqtSignal()
    upload_progress = pyqtSignal(int)
    upload_finished = pyqtSignal(str)


class UploadHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  

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
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f"""<!DOCTYPE html>
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0C0C0E; color: white; text-align: center; padding: 40px 20px; }}
                input[type="file"] {{ display: none; }}
                .btn {{ background: #5A8DEF; padding: 18px 40px; border-radius: 12px; color: white; border: none; font-size: 20px; margin: 20px; display: inline-block; cursor: pointer; font-weight: bold; box-shadow: 0 4px 15px rgba(90, 141, 239, 0.4); }}
                .btn:active {{ background: #4A7DDF; }}
                #progress {{ color: #AAAAAA; margin-top: 30px; font-size: 18px; }}
            </style>
            </head><body>
            <h2 style="font-size: 28px; margin-bottom: 10px;">Upload Photos</h2>
            <p style="color: #888888; font-size: 16px; line-height: 1.5; margin-bottom: 40px;">Select images from your device to beam them directly to Kiosk OS over your local network.</p>
            <label for="fileInput" class="btn">Select Images</label>
            <input type="file" id="fileInput" multiple accept="image/*" onchange="upload()">
            <div id="progress"></div>
            <script>
                setInterval(() => fetch('/ping').catch(()=>{{}}), 1000);
                async function upload() {{
                    const files = document.getElementById('fileInput').files;
                    let div = document.getElementById('progress');
                    for (let i=0; i<files.length; i++) {{
                        const file = files[i];
                        div.innerText = `Sending file ${{i+1}} of ${{files.length}}...`;
                        await fetch('/upload?filename=' + encodeURIComponent(file.name), {{
                            method: 'POST',
                            body: file,
                            headers: {{'Content-Type': 'application/octet-stream'}}
                        }});
                    }}
                    div.innerHTML = "<span style='color: #1ED760;'>All files sent successfully!</span>";
                    setTimeout(() => div.innerText="", 4000);
                    document.getElementById('fileInput').value = '';
                }}
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
    def __init__(self, signals, port=SERVER_PORT):
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
# FULL-SCREEN INTERACTIVE VIEWER & EDITOR COMPONENTS
# =================================================================
class SwipeableImageLabel(QLabel):
    """Custom label to intercept touch swipe gestures and tap events for fullscreen toggling."""
    swiped_left = pyqtSignal()
    swiped_right = pyqtSignal()
    tapped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.swipe_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.swipe_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.swipe_start_pos is not None:
            dx = event.position().toPoint().x() - self.swipe_start_pos.x()
            dy = event.position().toPoint().y() - self.swipe_start_pos.y()
            
            if dx > 60:
                self.swiped_right.emit() 
            elif dx < -60:
                self.swiped_left.emit()
            elif abs(dx) < 15 and abs(dy) < 15:
                self.tapped.emit()
                
        self.swipe_start_pos = None
        super().mouseReleaseEvent(event)


class EditorCanvas(QWidget):
    """A custom widget that handles the heavy lifting of displaying, cropping, drawing, and adjusting an image."""
    def __init__(self):
        super().__init__()
        self.mode = "view" # 'crop', 'draw', 'adjust', 'view'
        self.original_pixmap = QPixmap()
        
        # Transform State
        self.rot_angle = 0
        self.flip_h = False
        self.flip_v = False
        
        # Adjust State
        self.brightness = 0  # -100 to 100
        self.contrast = 0    # -100 to 100
        self.warmth = 0      # -100 to 100
        
        # Draw State
        self.paths = [] # list of {'points': [QPointF], 'color': QColor, 'width': int}
        self.current_path = None
        self.draw_color = QColor(226, 74, 74) # Default Red
        self.draw_width = 8
        
        # Crop State
        self.crop_rect_norm = QRectF(0, 0, 1, 1)
        self.crop_start = None
        
        self.draw_rect = QRect()

    def load_image(self, path):
        self.original_pixmap = QPixmap(path)
        self.reset_all()

    def reset_all(self):
        self.rot_angle = 0
        self.flip_h = False
        self.flip_v = False
        self.brightness = 0
        self.contrast = 0
        self.warmth = 0
        self.paths = []
        self.current_path = None
        self.crop_rect_norm = QRectF(0, 0, 1, 1)
        self.update()

    def apply_painter_adjustments(self, painter, rect):
        """Applies real-time hardware-accelerated adjustments using composition modes."""
        # Brightness
        if self.brightness > 0:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            painter.fillRect(rect, QColor(255, 255, 255, int(self.brightness * 1.2)))
        elif self.brightness < 0:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            val = 255 + int(self.brightness * 1.5)
            painter.fillRect(rect, QColor(val, val, val, 255))
            
        # Warmth / White Balance
        if self.warmth != 0:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
            if self.warmth > 0:
                painter.fillRect(rect, QColor(255, 150, 0, int(self.warmth * 0.7)))
            else:
                painter.fillRect(rect, QColor(0, 150, 255, int(abs(self.warmth) * 0.7)))

        # Contrast (Drawing image over itself using Overlay mode increases contrast)
        if self.contrast > 0:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
            painter.setOpacity(self.contrast / 150.0)
            painter.drawPixmap(rect, painter.device().copy(rect))
            painter.setOpacity(1.0)
        
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def get_transformed_pixmap(self, base_pix):
        if base_pix.isNull(): return base_pix
        t = QTransform()
        t.rotate(self.rot_angle)
        t.scale(-1 if self.flip_h else 1, -1 if self.flip_v else 1)
        return base_pix.transformed(t, Qt.TransformationMode.SmoothTransformation)

    def get_norm_pos(self, screen_pos):
        """Converts a screen pixel coordinate to a normalized 0.0-1.0 coordinate inside the image."""
        if self.draw_rect.width() == 0 or self.draw_rect.height() == 0:
            return QPointF(0, 0)
        nx = (screen_pos.x() - self.draw_rect.x()) / self.draw_rect.width()
        ny = (screen_pos.y() - self.draw_rect.y()) / self.draw_rect.height()
        return QPointF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))

    def mousePressEvent(self, event):
        if self.mode == "draw":
            self.current_path = [self.get_norm_pos(event.pos())]
            self.paths.append({'points': self.current_path, 'color': self.draw_color, 'width': self.draw_width})
            self.update()
        elif self.mode == "crop":
            self.crop_start = self.get_norm_pos(event.pos())
            self.crop_rect_norm = QRectF(self.crop_start, self.crop_start)
            self.update()

    def mouseMoveEvent(self, event):
        if self.mode == "draw" and self.current_path is not None:
            self.current_path.append(self.get_norm_pos(event.pos()))
            self.update()
        elif self.mode == "crop" and self.crop_start is not None:
            curr = self.get_norm_pos(event.pos())
            rect = QRectF(self.crop_start, curr).normalized()
            self.crop_rect_norm = rect.intersected(QRectF(0, 0, 1, 1))
            self.update()

    def mouseReleaseEvent(self, event):
        if self.mode == "draw":
            self.current_path = None
        elif self.mode == "crop":
            self.crop_start = None
            if self.crop_rect_norm.width() < 0.05 or self.crop_rect_norm.height() < 0.05:
                self.crop_rect_norm = QRectF(0, 0, 1, 1) # Reset if click was just a tap
            self.update()

    def paintEvent(self, event):
        if self.original_pixmap.isNull(): return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 1. Base Transform & Scale
        t_pix = self.get_transformed_pixmap(self.original_pixmap)
        scaled = t_pix.scaled(self.width() - 40, self.height() - 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self.draw_rect = QRect(x, y, scaled.width(), scaled.height())
        
        # 2. Draw Image & Adjustments
        painter.drawPixmap(self.draw_rect, scaled)
        self.apply_painter_adjustments(painter, self.draw_rect)
        
        # 3. Draw Markings
        for path_data in self.paths:
            points = path_data['points']
            if len(points) < 2: continue
            
            pen = QPen(path_data['color'], path_data['width'], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            qpath = QPainterPath()
            p0 = points[0]
            qpath.moveTo(x + p0.x() * scaled.width(), y + p0.y() * scaled.height())
            for pt in points[1:]:
                qpath.lineTo(x + pt.x() * scaled.width(), y + pt.y() * scaled.height())
            painter.drawPath(qpath)

        # 4. Draw Crop Overlay (Darkens outside, clear inside)
        if self.mode == "crop":
            cr = self.crop_rect_norm
            c_rect = QRectF(
                x + cr.x() * scaled.width(),
                y + cr.y() * scaled.height(),
                cr.width() * scaled.width(),
                cr.height() * scaled.height()
            )
            
            # Darken everything
            painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
            
            # Punch out the crop rect
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(c_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Draw border
            painter.setPen(QPen(QColor(255, 255, 255), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(c_rect)

    def save_to_file(self, target_path):
        """Renders the exact final layout to a full-resolution pixmap and saves it."""
        if self.original_pixmap.isNull(): return
        
        # Get base transformed full-res image
        t_pix = self.get_transformed_pixmap(self.original_pixmap)
        final_pix = QPixmap(t_pix.size())
        final_pix.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(final_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        full_rect = QRect(0, 0, t_pix.width(), t_pix.height())
        painter.drawPixmap(full_rect, t_pix)
        self.apply_painter_adjustments(painter, full_rect)
        
        for path_data in self.paths:
            points = path_data['points']
            if len(points) < 2: continue
            
            # Scale pen width proportionally to full image size
            scale_factor = t_pix.width() / float(max(1, self.draw_rect.width()))
            real_width = max(1, int(path_data['width'] * scale_factor))
            
            pen = QPen(path_data['color'], real_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            qpath = QPainterPath()
            p0 = points[0]
            qpath.moveTo(p0.x() * t_pix.width(), p0.y() * t_pix.height())
            for pt in points[1:]:
                qpath.lineTo(pt.x() * t_pix.width(), pt.y() * t_pix.height())
            painter.drawPath(qpath)
            
        painter.end()
        
        # Apply Final Crop
        if self.crop_rect_norm != QRectF(0, 0, 1, 1):
            cr = self.crop_rect_norm
            crop_rect = QRect(
                int(cr.x() * t_pix.width()),
                int(cr.y() * t_pix.height()),
                int(cr.width() * t_pix.width()),
                int(cr.height() * t_pix.height())
            )
            final_pix = final_pix.copy(crop_rect)
            
        final_pix.save(target_path)


class ImageEditorOverlay(QFrame):
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.setGeometry(0, 0, 1024, 600)
        self.setStyleSheet("background-color: #0A0A0C;")
        self.hide()
        
        self.current_path = ""
        
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Top Header ---
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #14141A;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedSize(100, 36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 18px; font-weight: bold;")
        btn_cancel.clicked.connect(self.hide)
        
        lbl_title = QLabel("Photo Editor")
        lbl_title.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_save = QPushButton("Save")
        btn_save.setFixedSize(100, 36)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #1ED760; color: #0E0E12; border-radius: 18px; font-weight: bold;")
        btn_save.clicked.connect(self.save_image)
        
        h_layout.addWidget(btn_cancel)
        h_layout.addWidget(lbl_title, stretch=1)
        h_layout.addWidget(btn_save)
        layout.addWidget(header)
        
        # --- Center Canvas ---
        self.canvas = EditorCanvas()
        layout.addWidget(self.canvas, stretch=1)
        
        # --- Bottom Tool Stack ---
        self.tools_stack = QStackedWidget()
        self.tools_stack.setFixedHeight(120)
        self.tools_stack.setStyleSheet("background-color: #14141A;")
        layout.addWidget(self.tools_stack)
        
        self.build_menus()
        
    def build_menus(self):
        # Page 0: Main Menu
        main_menu = QWidget()
        m_layout = QHBoxLayout(main_menu)
        m_layout.setContentsMargins(20, 20, 20, 20)
        m_layout.setSpacing(15)
        
        tools = [
            ("✂️ Crop", "crop"),
            ("⟳ Rotate", "rotate"),
            ("🖌️ Draw", "draw"),
            ("⚙️ Adjust", "adjust")
        ]
        
        for text, mode in tools:
            btn = QPushButton(text)
            btn.setFixedHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
            btn.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 12px;")
            btn.clicked.connect(lambda checked, m=mode: self.set_mode(m))
            m_layout.addWidget(btn)
        self.tools_stack.addWidget(main_menu)

        # Page 1: Crop Tools
        crop_menu = QWidget()
        c_layout = QHBoxLayout(crop_menu)
        c_layout.setContentsMargins(20, 20, 20, 20)
        lbl_crop = QLabel("Drag on the image to draw a crop box.\nTap to reset.")
        lbl_crop.setFont(QFont("Google Sans", 14))
        lbl_crop.setStyleSheet("color: #AAAAAA;")
        btn_c_done = QPushButton("Done Cropping")
        btn_c_done.setFixedSize(150, 45)
        btn_c_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 12px; font-weight: bold;")
        btn_c_done.clicked.connect(lambda: self.set_mode("view"))
        c_layout.addWidget(lbl_crop, stretch=1)
        c_layout.addWidget(btn_c_done)
        self.tools_stack.addWidget(crop_menu)

        # Page 2: Rotate Tools
        rot_menu = QWidget()
        r_layout = QHBoxLayout(rot_menu)
        r_layout.setContentsMargins(20, 20, 20, 20)
        
        btn_r90 = QPushButton("⟳ Rotate 90°")
        btn_fh = QPushButton("↔ Flip Horiz")
        btn_fv = QPushButton("↕ Flip Vert")
        
        for btn in [btn_r90, btn_fh, btn_fv]:
            btn.setFixedHeight(50)
            btn.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 12px; font-weight: bold; font-size: 14px;")
            r_layout.addWidget(btn)
            
        btn_r90.clicked.connect(self.do_rotate)
        btn_fh.clicked.connect(self.do_flip_h)
        btn_fv.clicked.connect(self.do_flip_v)
        
        btn_r_done = QPushButton("Done")
        btn_r_done.setFixedSize(100, 50)
        btn_r_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 12px; font-weight: bold;")
        btn_r_done.clicked.connect(lambda: self.set_mode("view"))
        r_layout.addWidget(btn_r_done)
        self.tools_stack.addWidget(rot_menu)
        
        # Page 3: Draw Tools
        draw_menu = QWidget()
        d_layout = QHBoxLayout(draw_menu)
        d_layout.setContentsMargins(20, 20, 20, 20)
        
        colors = ["#E24A4A", "#1ED760", "#5A8DEF", "#F39C12", "#FFFFFF", "#000000"]
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 20px; border: 2px solid #555;")
            btn.clicked.connect(lambda checked, color=c: self.set_draw_color(color))
            d_layout.addWidget(btn)
            
        d_layout.addStretch()
        btn_undo = QPushButton("Undo Path")
        btn_undo.setFixedSize(120, 45)
        btn_undo.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 12px; font-weight: bold;")
        btn_undo.clicked.connect(self.undo_draw)
        
        btn_d_done = QPushButton("Done")
        btn_d_done.setFixedSize(100, 45)
        btn_d_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 12px; font-weight: bold;")
        btn_d_done.clicked.connect(lambda: self.set_mode("view"))
        
        d_layout.addWidget(btn_undo)
        d_layout.addWidget(btn_d_done)
        self.tools_stack.addWidget(draw_menu)

        # Page 4: Adjust Tools
        adj_menu = QWidget()
        a_layout = QGridLayout(adj_menu)
        a_layout.setContentsMargins(20, 10, 20, 10)
        
        self.sld_bright = QSlider(Qt.Orientation.Horizontal)
        self.sld_bright.setRange(-100, 100)
        self.sld_bright.valueChanged.connect(self.update_adjustments)
        
        self.sld_contrast = QSlider(Qt.Orientation.Horizontal)
        self.sld_contrast.setRange(-100, 100)
        self.sld_contrast.valueChanged.connect(self.update_adjustments)
        
        self.sld_warmth = QSlider(Qt.Orientation.Horizontal)
        self.sld_warmth.setRange(-100, 100)
        self.sld_warmth.valueChanged.connect(self.update_adjustments)
        
        slider_css = "QSlider { background: transparent; height: 30px; } QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; } QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: #5A8DEF; border-radius: 8px; }"
        for sld in [self.sld_bright, self.sld_contrast, self.sld_warmth]:
            sld.setStyleSheet(slider_css)
            
        a_layout.addWidget(QLabel("Brightness", styleSheet="color: white; font-weight: bold;"), 0, 0)
        a_layout.addWidget(self.sld_bright, 0, 1)
        a_layout.addWidget(QLabel("Contrast", styleSheet="color: white; font-weight: bold;"), 1, 0)
        a_layout.addWidget(self.sld_contrast, 1, 1)
        a_layout.addWidget(QLabel("Warmth", styleSheet="color: white; font-weight: bold;"), 2, 0)
        a_layout.addWidget(self.sld_warmth, 2, 1)
        
        btn_a_done = QPushButton("Done")
        btn_a_done.setFixedSize(100, 45)
        btn_a_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 12px; font-weight: bold;")
        btn_a_done.clicked.connect(lambda: self.set_mode("view"))
        a_layout.addWidget(btn_a_done, 0, 2, 3, 1, Qt.AlignmentFlag.AlignVCenter)
        
        self.tools_stack.addWidget(adj_menu)

    def load_image(self, path):
        self.current_path = path
        self.canvas.load_image(path)
        self.set_mode("view")
        self.sld_bright.setValue(0)
        self.sld_contrast.setValue(0)
        self.sld_warmth.setValue(0)

    def set_mode(self, mode):
        self.canvas.mode = mode
        if mode == "view": self.tools_stack.setCurrentIndex(0)
        elif mode == "crop": self.tools_stack.setCurrentIndex(1)
        elif mode == "rotate": self.tools_stack.setCurrentIndex(2)
        elif mode == "draw": self.tools_stack.setCurrentIndex(3)
        elif mode == "adjust": self.tools_stack.setCurrentIndex(4)
        self.canvas.update()

    def do_rotate(self):
        self.canvas.rot_angle = (self.canvas.rot_angle + 90) % 360
        self.canvas.update()
    def do_flip_h(self):
        self.canvas.flip_h = not self.canvas.flip_h
        self.canvas.update()
    def do_flip_v(self):
        self.canvas.flip_v = not self.canvas.flip_v
        self.canvas.update()

    def set_draw_color(self, hex_col):
        self.canvas.draw_color = QColor(hex_col)
    def undo_draw(self):
        if self.canvas.paths:
            self.canvas.paths.pop()
            self.canvas.update()

    def update_adjustments(self):
        self.canvas.brightness = self.sld_bright.value()
        self.canvas.contrast = self.sld_contrast.value()
        self.canvas.warmth = self.sld_warmth.value()
        self.canvas.update()

    def save_image(self):
        self.canvas.save_to_file(self.current_path)
        self.on_save_callback()
        self.hide()


class ModernDialog(QDialog):
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
            btn_cancel.setStyleSheet("QPushButton { background: transparent; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; padding: 0 20px; } QPushButton:hover { background-color: rgba(255,255,255,10); }")
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)

        btn_accept = QPushButton(accept_text)
        btn_accept.setFixedHeight(45)
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.setStyleSheet("QPushButton { background-color: #E24A4A; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; border: none; padding: 0 25px; } QPushButton:hover { background-color: #C0392B; }")
        btn_accept.clicked.connect(self.accept)
        btn_layout.addWidget(btn_accept)

        bg_layout.addLayout(btn_layout)
        layout.addWidget(bg_frame)


class AlbumTransferDialog(QDialog):
    def __init__(self, parent, current_album, target_options):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(480, 360)
        self.chosen_album = None
        self.created_new_name = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        bg_frame = QFrame(self)
        bg_frame.setStyleSheet("background-color: #22222B; border-radius: 24px; border: 1px solid #33333F;")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(25, 25, 25, 20)

        lbl_title = QLabel("Move File to Album")
        lbl_title.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        bg_layout.addWidget(lbl_title)
        bg_layout.addSpacing(10)

        self.list_widget = QListWidget()
        QScroller.grabGesture(self.list_widget.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #14141A; border-radius: 12px; border: 1px solid #2C2C35; padding: 5px; color: white; font-size: 15px; outline: 0; }
            QListWidget::item { padding: 10px; border-radius: 8px; }
            QListWidget::item:selected { background-color: #5A8DEF; color: white; }
        """)
        
        for album in target_options:
            if album != current_album:
                self.list_widget.addItem(album)
        bg_layout.addWidget(self.list_widget)
        bg_layout.addSpacing(10)

        new_album_layout = QHBoxLayout()
        self.input_new_album = QLineEdit()
        self.input_new_album.setPlaceholderText("Or create a new album name...")
        self.input_new_album.setStyleSheet("QLineEdit { background-color: #14141A; border: 1px solid #2C2C35; border-radius: 8px; padding: 8px; color: white; font-size: 14px; }")
        new_album_layout.addWidget(self.input_new_album)
        
        btn_create = QPushButton("Create")
        btn_create.setStyleSheet("QPushButton { background-color: #343440; color: white; border-radius: 8px; padding: 8px 15px; font-weight: bold; } QPushButton:hover { background-color: #444455; }")
        btn_create.clicked.connect(self.create_custom_album)
        new_album_layout.addWidget(btn_create)
        bg_layout.addLayout(new_album_layout)
        bg_layout.addSpacing(15)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("QPushButton { background: transparent; color: #888888; font-weight: bold; font-size: 15px; padding: 5px 15px; border: none; }")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_move = QPushButton("Move File")
        btn_move.setStyleSheet("QPushButton { background-color: #5A8DEF; color: white; font-weight: bold; font-size: 15px; border-radius: 8px; padding: 8px 20px; }")
        btn_move.clicked.connect(self.confirm_move)
        actions.addWidget(btn_move)
        bg_layout.addLayout(actions)

        layout.addWidget(bg_frame)

    def create_custom_album(self):
        text = self.input_new_album.text().strip()
        if text:
            self.created_new_name = text
            self.chosen_album = text
            self.accept()

    def confirm_move(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            self.chosen_album = selected_items[0].text()
            self.accept()
        elif self.input_new_album.text().strip():
            self.create_custom_album()


class ImageButton(QPushButton):
    def __init__(self, img_path, click_cb):
        super().__init__()
        self.img_path = img_path
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background-color: #1C1C22; border-radius: 16px; border: 1px solid #2C2C35; } QPushButton:hover { border-color: #5A8DEF; }")
        
        pix = QPixmap(img_path)
        if not pix.isNull():
            side = min(pix.width(), pix.height())
            x = (pix.width() - side) // 2
            y = (pix.height() - side) // 2
            cropped = pix.copy(x, y, side, side)
            scaled_pix = cropped.scaled(156, 196, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            rounded = QPixmap(156, 156)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, 156, 156, 14, 14)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled_pix)
            painter.end()
            self.setIcon(QIcon(rounded))
            self.setIconSize(QSize(156, 156))
            
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
        
        # Base Album Map Config
        self.albums = ["Photos", "Screenshots", "Videos"]
        self.current_selected_album = "Photos"
        self.all_image_paths = []
        
        # System Folders to completely ignore during scanning
        self.ignored_folders = [".", "__", "apps", "components", "fonts", "icons", "venv", "browser_data"]
        
        # --- 1. Dashboard View with Navigation Sidebar ---
        self.grid_page = QWidget()
        dashboard_layout = QHBoxLayout(self.grid_page)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(0)

        # Left Sidebar Navigation Panel
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background-color: #14141A; border-right: 1px solid #22222A;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 20)
        sidebar_layout.setSpacing(10)

        lbl_sections = QLabel("Albums")
        lbl_sections.setFont(QFont("Google Sans", 15, QFont.Weight.Bold))
        lbl_sections.setStyleSheet("color: #666670; margin-left: 10px; margin-bottom: 5px;")
        sidebar_layout.addWidget(lbl_sections)

        self.album_list_widget = QListWidget()
        QScroller.grabGesture(self.album_list_widget.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.album_list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #AAAAAA; outline: 0; }
            QListWidget::item { padding: 12px 15px; margin-bottom: 4px; border-radius: 10px; font-weight: bold; font-size: 15px; }
            QListWidget::item:hover { background-color: rgba(255, 255, 255, 8); color: white; }
            QListWidget::item:selected { background-color: rgba(90, 141, 239, 30); color: #5A8DEF; }
        """)
        self.album_list_widget.itemClicked.connect(self.on_album_nav_clicked)
        sidebar_layout.addWidget(self.album_list_widget)
        sidebar_layout.addStretch()

        dashboard_layout.addWidget(self.sidebar)

        # Right Panel Grid Content Space
        self.main_content_frame = QWidget()
        right_panel_layout = QVBoxLayout(self.main_content_frame)
        right_panel_layout.setContentsMargins(30, 25, 30, 30)
        
        header = QHBoxLayout()
        self.lbl_album_title = QLabel("Photos")
        self.lbl_album_title.setFont(QFont("Google Sans", 28, QFont.Weight.Bold))
        header.addWidget(self.lbl_album_title)
        header.addStretch()
        
        self.lbl_connected = QLabel("📱 Device connected.")
        self.lbl_connected.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        self.lbl_connected.setStyleSheet("color: #1ED760;")
        self.lbl_connected.hide()
        header.addWidget(self.lbl_connected)
        header.addSpacing(20)
        
        self.btn_upload = QPushButton("  Upload")
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
        self.btn_upload.setStyleSheet("QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; padding: 0px 20px; font-weight: bold; font-size: 16px; border: none; height: 45px; } QPushButton:hover { background-color: #4A7DDF; }")
        self.btn_upload.clicked.connect(self.show_qr_code)
        header.addWidget(self.btn_upload)
        
        if self.on_close:
            header.addSpacing(15)
            btn_close = QPushButton("✕")
            btn_close.setFixedSize(45, 45)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
            btn_close.setStyleSheet("QPushButton { background-color: #2C2C35; color: #AAAAAA; border-radius: 22px; border: none; } QPushButton:hover { background-color: #E24A4A; color: white; }")
            btn_close.clicked.connect(self.shutdown_and_close)
            header.addWidget(btn_close)
            
        right_panel_layout.addLayout(header)
        
        self.upload_progress = QProgressBar()
        self.upload_progress.setTextVisible(False)
        self.upload_progress.setFixedHeight(6)
        self.upload_progress.setStyleSheet("""
            QProgressBar { background: #1C1C22; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5A8DEF, stop:1 #9B59B6); border-radius: 3px; }
        """)
        self.upload_progress.hide()
        right_panel_layout.addWidget(self.upload_progress)
        
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
        self.grid.setSpacing(20)
        
        self.scroll.setWidget(self.grid_container)
        right_panel_layout.addWidget(self.scroll)
        dashboard_layout.addWidget(self.main_content_frame)
        self.stack.addWidget(self.grid_page)
        
        # --- 2. Fullscreen Interactive Viewer Viewport ---
        self.fs_page = QWidget()
        self.fs_page.setStyleSheet("background-color: #000000;")
        fs_main_layout = QVBoxLayout(self.fs_page)
        fs_main_layout.setContentsMargins(0, 0, 0, 0)
        fs_main_layout.setSpacing(0)
        
        self.fs_header_widget = QWidget()
        self.fs_header_widget.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,180), stop:1 rgba(0,0,0,0));")
        fs_header = QHBoxLayout(self.fs_header_widget)
        fs_header.setContentsMargins(20, 20, 20, 20)
        
        self.btn_back = QPushButton("← Back")
        self.btn_back.setFixedSize(110, 45)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("QPushButton { background-color: rgba(255,255,255,30); color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { background-color: rgba(255,255,255,50); }")
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        fs_header.addWidget(self.btn_back)
        fs_header.addStretch()

        self.btn_edit = QPushButton("✏️ Edit")
        self.btn_edit.setFixedSize(100, 45)
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setStyleSheet("QPushButton { background-color: rgba(90, 141, 239, 60); color: #5A8DEF; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { background-color: #5A8DEF; color: white; }")
        self.btn_edit.clicked.connect(self.trigger_image_editor)
        fs_header.addWidget(self.btn_edit)
        fs_header.addSpacing(10)

        self.btn_move = QPushButton("📦 Move")
        self.btn_move.setFixedSize(100, 45)
        self.btn_move.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_move.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 30); color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { background-color: rgba(255, 255, 255, 50); }")
        self.btn_move.clicked.connect(self.trigger_album_migration)
        fs_header.addWidget(self.btn_move)
        fs_header.addSpacing(10)
        
        self.btn_del = QPushButton("🗑️ Delete")
        self.btn_del.setFixedSize(110, 45)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setStyleSheet("QPushButton { background-color: rgba(226, 74, 74, 60); color: #E24A4A; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { background-color: #E24A4A; color: white; }")
        self.btn_del.clicked.connect(self.delete_current_image)
        fs_header.addWidget(self.btn_del)
        
        fs_main_layout.addWidget(self.fs_header_widget)
        
        self.lbl_fs_img = SwipeableImageLabel()
        self.lbl_fs_img.swiped_right.connect(self.navigate_previous_media)
        self.lbl_fs_img.swiped_left.connect(self.navigate_next_media)
        self.lbl_fs_img.tapped.connect(self.toggle_immersive_fullscreen)
        fs_main_layout.addWidget(self.lbl_fs_img, stretch=1)

        self.stack.addWidget(self.fs_page)

        # --- 3. QR Code Viewport Panel ---
        self.qr_page = QWidget()
        qr_layout = QVBoxLayout(self.qr_page)
        qr_layout.setContentsMargins(40, 30, 40, 30)
        
        btn_qr_back = QPushButton("← Back")
        btn_qr_back.setFixedSize(110, 45)
        btn_qr_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_qr_back.setStyleSheet("QPushButton { background-color: #2C2C35; color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none; } QPushButton:hover { background-color: #383845; }")
        btn_qr_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        qr_layout.addWidget(btn_qr_back, alignment=Qt.AlignmentFlag.AlignLeft)
        qr_layout.addStretch()
        
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setFixedSize(250, 250)
        self.lbl_qr.setStyleSheet("background-color: #1C1C22; border-radius: 16px;")
        qr_layout.addWidget(self.lbl_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        qr_layout.addSpacing(20)
        
        self.lbl_qr_inst = QLabel("Scan this code with your phone to upload images.")
        self.lbl_qr_inst.setFont(QFont("Google Sans", 18))
        self.lbl_qr_inst.setStyleSheet("color: #AAAAAA;")
        self.lbl_qr_inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self.lbl_qr_inst, alignment=Qt.AlignmentFlag.AlignCenter)
        qr_layout.addStretch()
        self.stack.addWidget(self.qr_page)
        
        # --- Internal Overlays ---
        self.editor_overlay = ImageEditorOverlay(self, self.on_editor_saved)

        self.current_img_path = None
        self.scan_and_sync_local_albums()
        self.populate_sidebar_items()
        self.load_images()

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

    def toggle_immersive_fullscreen(self):
        if self.fs_header_widget.isVisible():
            self.fs_header_widget.hide()
        else:
            self.fs_header_widget.show()

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
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return '127.0.0.1'

    def show_qr_code(self):
        ip = self.get_local_ip()
        url = f"http://{ip}:{SERVER_PORT}"
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(url)}&bgcolor=1C1C22&color=FFFFFF"
        
        self.lbl_qr.setText("Generating QR...")
        self.lbl_qr.setStyleSheet("background-color: #1C1C22; color: #5A8DEF; font-size: 16px; border-radius: 16px;")
        
        self.lbl_qr_inst.setText(f"Scan the QR code or visit this local address:\n{url}")
        
        self.qr_thread = QRFetchThread(api_url)
        self.qr_thread.on_qr_ready.connect(self.set_qr_image)
        self.qr_thread.start()
        self.stack.setCurrentIndex(2)

    def set_qr_image(self, pix):
        self.lbl_qr.setPixmap(pix)
        self.lbl_qr.setStyleSheet("background-color: transparent;")

    def scan_and_sync_local_albums(self):
        if os.path.exists("Pictures") and not os.path.exists("photos"):
            try: os.rename("Pictures", "photos")
            except Exception: pass
                
        base_directories = ["photos", "screenshots", "videos"]
        for d in base_directories:
            if not os.path.exists(d): os.makedirs(d, exist_ok=True)
            norm_name = d.title()
            if norm_name not in self.albums: self.albums.append(norm_name)
                
        for entry in os.listdir("."):
            if os.path.isdir(entry):
                should_ignore = False
                for ig in self.ignored_folders:
                    if entry.startswith(ig):
                        should_ignore = True
                        break
                if not should_ignore and entry not in base_directories:
                    if entry not in self.albums: self.albums.append(entry)

    def populate_sidebar_items(self):
        self.album_list_widget.clear()
        for folder in self.albums:
            item = QListWidgetItem(folder)
            self.album_list_widget.addItem(item)
            if folder == self.current_selected_album:
                self.album_list_widget.setCurrentItem(item)

    def on_album_nav_clicked(self, item):
        self.current_selected_album = item.text()
        self.lbl_album_title.setText(self.current_selected_album)
        self.load_images()

    def load_images(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.deleteLater()
            
        target_dir = self.current_selected_album.lower() if self.current_selected_album in ["Screenshots", "Photos", "Videos"] else self.current_selected_album
        self.all_image_paths = []
        
        if os.path.exists(target_dir):
            for f in os.listdir(target_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    self.all_image_paths.append(os.path.join(target_dir, f))
                        
        self.all_image_paths.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        if not self.all_image_paths:
            lbl_empty = QLabel("No images in this album.")
            lbl_empty.setFont(QFont("Google Sans", 16))
            lbl_empty.setStyleSheet("color: #666670;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.grid.addWidget(lbl_empty, 0, 0)
            return
            
        cols = 4
        for i, path in enumerate(self.all_image_paths):
            btn = ImageButton(path, self.open_image)
            self.grid.addWidget(btn, i // cols, i % cols)
            
    def open_image(self, path):
        self.current_img_path = path
        pix = QPixmap(path)
        if not pix.isNull():
            scaled = pix.scaled(1024, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_fs_img.setPixmap(scaled)
        self.stack.setCurrentIndex(1)
        
    def navigate_previous_media(self):
        if self.current_img_path in self.all_image_paths:
            idx = self.all_image_paths.index(self.current_img_path)
            if idx > 0: self.open_image(self.all_image_paths[idx - 1])
            else: self.open_image(self.all_image_paths[-1])

    def navigate_next_media(self):
        if self.current_img_path in self.all_image_paths:
            idx = self.all_image_paths.index(self.current_img_path)
            if idx < len(self.all_image_paths) - 1: self.open_image(self.all_image_paths[idx + 1])
            else: self.open_image(self.all_image_paths[0])

    def trigger_image_editor(self):
        if self.current_img_path:
            self.editor_overlay.load_image(self.current_img_path)
            self.editor_overlay.show()
            self.editor_overlay.raise_()

    def on_editor_saved(self):
        self.load_images()
        self.open_image(self.current_img_path)

    def trigger_album_migration(self):
        if not self.current_img_path: return
        dialog = AlbumTransferDialog(self, self.current_selected_album, self.albums)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.chosen_album:
            dest_dir = dialog.chosen_album.lower() if dialog.chosen_album in ["Screenshots", "Photos", "Videos"] else dialog.chosen_album
            os.makedirs(dest_dir, exist_ok=True)
            filename = os.path.basename(self.current_img_path)
            dest_path = os.path.join(dest_dir, filename)
            try:
                shutil.move(self.current_img_path, dest_path)
                self.scan_and_sync_local_albums()
                self.populate_sidebar_items()
                self.load_images()
                self.stack.setCurrentIndex(0)
            except Exception as e: print(f"Error transferring file: {e}")

    def delete_current_image(self):
        if self.current_img_path and os.path.exists(self.current_img_path):
            dialog = ModernDialog(self, "Delete Image", "Are you sure you want to permanently delete this image?", "Delete")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    os.remove(self.current_img_path)
                    self.load_images()
                    self.stack.setCurrentIndex(0)
                except Exception as e: print(f"Failed to delete image: {e}")

    def shutdown_and_close(self):
        if hasattr(self, 'server_thread'):
            self.server_thread.stop()
            self.server_thread.wait()
        if self.on_close:
            self.on_close()