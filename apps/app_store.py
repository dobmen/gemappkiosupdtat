import os
import ssl
import urllib.request
import json
import time  
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer, pyqtProperty
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QImage, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QProgressBar, QMessageBox, QScroller, QStackedWidget, QGridLayout, QLineEdit, QDialog
)

MANIFEST_URL = "https://raw.githubusercontent.com/dobmen/gemappkiosstor/main/store_manifest.json"


def get_scale_factor():
    screen = QGuiApplication.primaryScreen()
    return max(1.0, screen.size().width() / 1024.0) if screen else 1.0


class FadeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._alpha = 0
        self.hide()

    @pyqtProperty(int)
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(12, 12, 14, self._alpha))


class FetchManifestThread(QThread):
    on_success = pyqtSignal(list)
    on_error = pyqtSignal(str)

    def run(self):
        try:
            cache_busting_url = f"{MANIFEST_URL}?t={int(time.time())}"
            req = urllib.request.Request(
                cache_busting_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Kiosk OS)'}
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                self.on_success.emit(data.get("apps", []))
        except Exception as e:
            self.on_error.emit(str(e))


class DownloadAppThread(QThread):
    on_progress = pyqtSignal(int)
    on_finished = pyqtSignal(str)
    on_error = pyqtSignal(str)

    def __init__(self, app_data):
        super().__init__()
        self.app_data = app_data

    def run(self):
        failed_url = "Unknown"
        try:
            self.on_progress.emit(10)
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            icon_url = self.app_data.get("icon_url", "").strip()
            script_url = self.app_data.get("script_url", "").strip()

            if icon_url:
                failed_url = icon_url
                icon_filename = os.path.basename(icon_url)
                icon_path = os.path.join("icons", icon_filename)
                os.makedirs("icons", exist_ok=True)
                
                req_icon = urllib.request.Request(icon_url, headers={'User-Agent': 'KioskOS'})
                with urllib.request.urlopen(req_icon, timeout=10, context=ctx) as response:
                    with open(icon_path, 'wb') as f:
                        f.write(response.read())
            
            self.on_progress.emit(50)

            target_dir = "clockfaces" if self.app_data.get("type") == "clockface" else "apps"
            os.makedirs(target_dir, exist_ok=True)
            
            failed_url = script_url
            temp_script = os.path.join(target_dir, "update.tmp")
            
            req_script = urllib.request.Request(script_url, headers={'User-Agent': 'KioskOS'})
            with urllib.request.urlopen(req_script, timeout=10, context=ctx) as response:
                with open(temp_script, 'wb') as f:
                    f.write(response.read())
                    
            self.on_progress.emit(80)
            
            target_script = os.path.join(target_dir, self.app_data["filename"])
            os.replace(temp_script, target_script)
            
            ver_path = target_script.replace(".py", ".ver")
            with open(ver_path, "w") as f:
                f.write(str(self.app_data["version"]))
            self.on_progress.emit(100)
                
            self.on_finished.emit(self.app_data["name"])
        except Exception as e:
            self.on_error.emit(f"Failed to download from GitHub.\nBroken Link: {failed_url}\nError: {str(e)}")


class NetworkImageThread(QThread):
    on_image_ready = pyqtSignal(object, QImage, QImage)
    
    def __init__(self, url, target_widget, width, height, radius=8):
        super().__init__()
        self.url = url.strip()
        self.target_widget = target_widget
        self.width = width
        self.height = height
        self.radius = radius

    def run(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(self.url, headers={'User-Agent': 'KioskOS'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                data = response.read()
                
                orig_img = QImage()
                orig_img.loadFromData(data)

                scaled = orig_img.scaled(self.width, self.height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                
                thumb_img = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
                thumb_img.fill(Qt.GlobalColor.transparent)

                p = QPainter(thumb_img)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                clip = QPainterPath()
                clip.addRoundedRect(0, 0, self.width, self.height, self.radius, self.radius)
                p.setClipPath(clip)
                
                x = (self.width - scaled.width()) // 2
                y = (self.height - scaled.height()) // 2
                p.drawImage(x, y, scaled)
                p.end()
                
                self.on_image_ready.emit(self.target_widget, thumb_img, orig_img)
        except Exception as e:
            pass


class ClickableScreenshot(QLabel):
    clicked = pyqtSignal(QPixmap)
    
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.original_pixmap = None
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.original_pixmap and not self.original_pixmap.isNull():
                self.clicked.emit(self.original_pixmap)
            elif self.pixmap():
                self.clicked.emit(self.pixmap())
        super().mouseReleaseEvent(event)


class AppCard(QFrame):
    def __init__(self, app_data, install_callback, open_details_callback):
        super().__init__()
        self.app_data = app_data
        self.install_callback = install_callback
        self.open_details_callback = open_details_callback
        scale = get_scale_factor()
        
        self.setMinimumHeight(int(145 * scale))
        self.setStyleSheet("""
            AppCard { background-color: #1C1C22; border: 1px solid #2C2C35; border-radius: 12px; }
            AppCard:hover { background-color: #24242E; border-color: #3C3C45; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(int(20 * scale), int(18 * scale), int(20 * scale), int(18 * scale))
        layout.setSpacing(int(15 * scale))

        icon_size = int(60 * scale)
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(icon_size, icon_size)
        colors = ["#E24A4A", "#5A8DEF", "#F39C12", "#27AE60", "#8E44AD", "#9B59B6"]
        c = colors[len(app_data.get('name', 'A')) % len(colors)]
        self.lbl_icon.setStyleSheet(f"background-color: {c}; border-radius: {icon_size//2}px; color: white;")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setFont(QFont("Google Sans", int(28 * scale), QFont.Weight.Bold))
        self.lbl_icon.setText(app_data.get('name', 'A')[0].upper())
        
        if app_data.get("icon_url"):
            self.icon_thread = NetworkImageThread(app_data["icon_url"], self.lbl_icon, icon_size, icon_size, radius=icon_size//2)
            self.icon_thread.on_image_ready.connect(self.set_icon)
            self.icon_thread.start()

        layout.addWidget(self.lbl_icon)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        lbl_name = QLabel(f"{app_data['name']} (v{app_data['version']})")
        lbl_name.setFont(QFont("Google Sans", int(18 * scale), QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white; border: none; background: transparent;")
        
        lbl_author = QLabel(f"By {app_data.get('author', 'Unknown')}")
        lbl_author.setFont(QFont("Google Sans", int(12 * scale)))
        lbl_author.setStyleSheet("color: #888888; border: none; background: transparent;")
        
        lbl_desc = QLabel(app_data['description'])
        lbl_desc.setFont(QFont("Google Sans", int(14 * scale)))
        lbl_desc.setStyleSheet("color: #CCCCCC; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)

        info_layout.addWidget(lbl_name)
        info_layout.addWidget(lbl_author)
        info_layout.addWidget(lbl_desc)

        target_dir = "clockfaces" if app_data.get("type") == "clockface" else "apps"
        local_script = os.path.join(target_dir, app_data["filename"])
        ver_path = local_script.replace(".py", ".ver")
        
        self.is_installed = os.path.exists(local_script)
        installed_version = "0.0.0"
        if os.path.exists(ver_path):
            with open(ver_path, "r") as f:
                installed_version = f.read().strip()
        
        self.needs_update = self.is_installed and (str(app_data["version"]) > installed_version)

        self.btn_install = QPushButton()
        self.btn_install.setFixedSize(int(130 * scale), int(45 * scale))
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button_style()
        self.btn_install.clicked.connect(self.on_install_click)

        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.btn_install, alignment=Qt.AlignmentFlag.AlignVCenter)

    def update_button_style(self):
        scale = get_scale_factor()
        if self.needs_update:
            self.btn_install.setText("Update")
            self.btn_install.setStyleSheet(f"""
                QPushButton {{ background-color: #5A8DEF; color: white; border-radius: {int(22 * scale)}px; font-size: {int(16 * scale)}px; font-weight: bold; border: none; }}
                QPushButton:hover {{ background-color: #4A7DDF; }}
            """)
        elif self.is_installed:
            self.btn_install.setText("Installed")
            self.btn_install.setStyleSheet(f"""
                QPushButton {{ background-color: #2C2C35; color: #AAAAAA; border-radius: {int(22 * scale)}px; font-size: {int(16 * scale)}px; font-weight: bold; border: none; }}
            """)
            self.btn_install.setEnabled(False)
        else:
            self.btn_install.setText("Install")
            self.btn_install.setStyleSheet(f"""
                QPushButton {{ background-color: #1ED760; color: white; border-radius: {int(22 * scale)}px; font-size: {int(16 * scale)}px; font-weight: bold; border: none; }}
                QPushButton:hover {{ background-color: #1DB954; }}
            """)

    def set_icon(self, widget, thumb, orig):
        self.lbl_icon.setText("")
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_icon.setPixmap(QPixmap.fromImage(thumb))

    def on_install_click(self):
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Updating..." if self.needs_update else "Installing...")
        self.install_callback(self.app_data, self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.btn_install.geometry().contains(event.position().toPoint()):
                self.open_details_callback(self.app_data, self)
        super().mouseReleaseEvent(event)


class AppDetailsSection(QWidget):
    def __init__(self, on_back_callback, install_callback, on_screenshot_click):
        super().__init__()
        self.install_callback = install_callback
        self.on_screenshot_click = on_screenshot_click
        self.active_card = None
        self.app_data = None
        self.active_threads = []
        self.scale = get_scale_factor()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(15)

        nav_layout = QHBoxLayout()
        btn_back = QPushButton("◀ Catalog")
        btn_back.setFixedSize(int(110 * self.scale), int(36 * self.scale))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f"background-color: #2C2C35; color: white; border-radius: 8px; font-weight: bold; font-size: {int(14 * self.scale)}px; border: none;")
        btn_back.clicked.connect(on_back_callback)
        nav_layout.addWidget(btn_back)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(10, 10, 10, 50)
        self.content_layout.setSpacing(int(25 * self.scale))
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.identity_card = QFrame()
        self.identity_card.setStyleSheet("background-color: #1C1C22; border: 1px solid #2C2C35; border-radius: 16px;")
        id_layout = QHBoxLayout(self.identity_card)
        id_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        id_layout.setSpacing(int(20 * self.scale))

        icon_size = int(80 * self.scale)
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(icon_size, icon_size)
        self.lbl_icon.setStyleSheet(f"background-color: #2C2C35; border-radius: {icon_size//2}px;")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.lbl_name = QLabel()
        self.lbl_name.setFont(QFont("Google Sans", int(22 * self.scale), QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: white; border: none;")
        
        self.lbl_author_cat = QLabel()
        self.lbl_author_cat.setFont(QFont("Google Sans", int(13 * self.scale)))
        self.lbl_author_cat.setStyleSheet("color: #888888; border: none;")
        title_box.addWidget(self.lbl_name)
        title_box.addWidget(self.lbl_author_cat)

        self.btn_action = QPushButton()
        self.btn_action.setFixedSize(int(140 * self.scale), int(48 * self.scale))
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.clicked.connect(self.on_action_clicked)

        id_layout.addWidget(self.lbl_icon)
        id_layout.addLayout(title_box, stretch=1)
        id_layout.addWidget(self.btn_action)
        self.content_layout.addWidget(self.identity_card)

        self.scr_scroll = QScrollArea()
        self.scr_scroll.setFixedHeight(int(170 * self.scale))
        self.scr_scroll.setWidgetResizable(True)
        self.scr_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scr_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.scr_container = QWidget()
        self.scr_layout = QHBoxLayout(self.scr_container)
        self.scr_layout.setContentsMargins(0, 0, 0, 0)
        self.scr_layout.setSpacing(int(14 * self.scale))
        self.scr_scroll.setWidget(self.scr_container)
        self.content_layout.addWidget(self.scr_scroll)

        self.lbl_desc_title = QLabel("About this application")
        self.lbl_desc_title.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        self.lbl_desc = QLabel()
        self.lbl_desc.setFont(QFont("Google Sans", int(14 * self.scale)))
        self.lbl_desc.setStyleSheet("color: #CCCCCC; line-height: 22px;")
        self.lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_desc_title)
        self.content_layout.addWidget(self.lbl_desc)

        self.spec_card = QFrame()
        self.spec_card.setStyleSheet("background-color: #14141A; border-radius: 12px; border: 1px solid #22222A;")
        spec_layout = QGridLayout(self.spec_card)
        spec_layout.setContentsMargins(int(20 * self.scale), int(15 * self.scale), int(20 * self.scale), int(15 * self.scale))
        spec_layout.setSpacing(int(15 * self.scale))

        self.lbl_meta_ver_title = QLabel("Version")
        self.lbl_meta_ver_title.setStyleSheet(f"color: #666670; font-size: {int(13 * self.scale)}px; font-weight: bold; border: none;")
        self.lbl_meta_ver = QLabel()
        self.lbl_meta_ver.setStyleSheet(f"color: white; font-size: {int(14 * self.scale)}px; border: none;")
        
        self.lbl_meta_size_title = QLabel("Storage Needed")
        self.lbl_meta_size_title.setStyleSheet(f"color: #666670; font-size: {int(13 * self.scale)}px; font-weight: bold; border: none;")
        self.lbl_meta_size = QLabel()
        self.lbl_meta_size.setStyleSheet(f"color: white; font-size: {int(14 * self.scale)}px; border: none;")

        spec_layout.addWidget(self.lbl_meta_ver_title, 0, 0)
        spec_layout.addWidget(self.lbl_meta_ver, 1, 0)
        spec_layout.addWidget(self.lbl_meta_size_title, 0, 1)
        spec_layout.addWidget(self.lbl_meta_size, 1, 1)
        self.content_layout.addWidget(self.spec_card)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def apply_downloaded_image(self, widget, thumb_img, orig_img):
        try:
            thumb_pix = QPixmap.fromImage(thumb_img)
            orig_pix = QPixmap.fromImage(orig_img)
            
            widget.setPixmap(thumb_pix)
            widget.setStyleSheet("background-color: transparent;")
            if hasattr(widget, 'original_pixmap'):
                widget.original_pixmap = orig_pix
        except RuntimeError:
            pass

    def populate_details(self, app_data, card_reference):
        self.app_data = app_data
        self.active_card = card_reference

        for t in self.active_threads:
            try:
                t.disconnect()
                t.deleteLater()
            except Exception:
                pass
        self.active_threads.clear()

        self.lbl_name.setText(app_data['name'])
        
        cat_text = "Clockface" if app_data.get('type') == 'clockface' else app_data.get('category', 'Utility')
        self.lbl_author_cat.setText(f"By {app_data.get('author', 'Unknown')} • {cat_text}")
        
        desc_text = app_data.get('expanded_description') or app_data.get('description', '')
        self.lbl_desc.setText(desc_text)
        
        self.lbl_meta_ver.setText(str(app_data['version']))
        self.lbl_meta_size.setText(app_data.get('storage_needed', 'Unknown Size'))

        icon_size = int(80 * self.scale)
        icon_pix = QPixmap(icon_size, icon_size)
        icon_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(icon_pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#5A8DEF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, icon_size, icon_size)
        p.setPen(QColor("white"))
        p.setFont(QFont("Google Sans", int(26 * self.scale), QFont.Weight.Bold))
        p.drawText(QRect(0, 0, icon_size, icon_size), Qt.AlignmentFlag.AlignCenter, app_data['name'][0].upper())
        p.end()
        self.lbl_icon.setPixmap(icon_pix)

        if app_data.get('icon_url'):
            icon_thread = NetworkImageThread(app_data['icon_url'], self.lbl_icon, icon_size, icon_size, radius=icon_size//2)
            icon_thread.on_image_ready.connect(self.apply_downloaded_image)
            icon_thread.start()
            self.active_threads.append(icon_thread)

        for i in reversed(range(self.scr_layout.count())):
            self.scr_layout.itemAt(i).widget().setParent(None)

        screenshots = app_data.get('screenshots', [])
        if screenshots:
            self.scr_scroll.show()
            scr_w = int(240 * self.scale)
            scr_h = int(140 * self.scale)
            for s_url in screenshots:
                scr_lbl = ClickableScreenshot()
                scr_lbl.clicked.connect(self.on_screenshot_click)
                scr_lbl.setFixedSize(scr_w, scr_h)
                scr_lbl.setStyleSheet("background-color: #2C2C35; border-radius: 8px; border: 1px solid #3C3C45;")
                scr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.scr_layout.addWidget(scr_lbl)
                
                scr_thread = NetworkImageThread(s_url, scr_lbl, scr_w, scr_h, radius=8)
                scr_thread.on_image_ready.connect(self.apply_downloaded_image)
                scr_thread.start()
                self.active_threads.append(scr_thread)
        else:
            self.scr_scroll.hide()

        self.update_action_button_style()

    def update_action_button_style(self):
        if not self.active_card: return
        self.btn_action.setEnabled(True)
        if self.active_card.needs_update:
            self.btn_action.setText("⬆ Update")
            self.btn_action.setStyleSheet(f"background-color: #F39C12; color: white; border-radius: 8px; font-weight: bold; font-size: {int(15 * self.scale)}px; border: none;")
        elif self.active_card.is_installed:
            self.btn_action.setText("Installed")
            self.btn_action.setStyleSheet(f"background-color: #2E2E38; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: {int(15 * self.scale)}px; border: none;")
        else:
            self.btn_action.setText("⬇ Install")
            self.btn_action.setStyleSheet(f"background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: {int(15 * self.scale)}px; border: none;")

    def on_action_clicked(self):
        self.btn_action.setEnabled(False)
        self.btn_action.setText("Processing...")
        self.install_callback(self.app_data, self.active_card)


class AppStorePage(QWidget):
    def __init__(self, on_install_success=None):
        super().__init__()
        self.setStyleSheet("background-color: #0C0C0E;")
        self.on_install_success = on_install_success
        self.full_catalog_cache = []
        self._active_threads = set()
        self.scale = get_scale_factor()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(40 * self.scale), int(20 * self.scale), int(40 * self.scale), int(30 * self.scale))
        layout.setSpacing(int(15 * self.scale))

        self.header_stack = QStackedWidget()
        self.header_stack.setFixedHeight(int(54 * self.scale))
        
        header_normal = QWidget()
        normal_layout = QHBoxLayout(header_normal)
        normal_layout.setContentsMargins(0, 0, 0, 0)
        normal_layout.setSpacing(int(10 * self.scale))

        self.title_lbl = QLabel("App Store")
        self.title_lbl.setFont(QFont("Google Sans", int(26 * self.scale), QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: white;")
        normal_layout.addWidget(self.title_lbl)
        normal_layout.addStretch()

        self.btn_tab_all = QPushButton("Apps")
        self.btn_tab_faces = QPushButton("Clockfaces")
        self.btn_tab_installed = QPushButton("Installed")
        self.btn_tab_updates = QPushButton("Updates")
        
        self.tab_active_css = f"background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: {int(13 * self.scale)}px; padding: 6px 14px; border: none;"
        self.tab_inactive_css = f"background-color: #2C2C35; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: {int(13 * self.scale)}px; padding: 6px 14px; border: none;"
        
        self.btn_tab_all.setStyleSheet(self.tab_active_css)
        self.btn_tab_faces.setStyleSheet(self.tab_inactive_css)
        self.btn_tab_installed.setStyleSheet(self.tab_inactive_css)
        self.btn_tab_updates.setStyleSheet(self.tab_inactive_css)

        for btn in [self.btn_tab_all, self.btn_tab_faces, self.btn_tab_installed, self.btn_tab_updates]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            normal_layout.addWidget(btn)

        self.btn_tab_all.clicked.connect(lambda: self.switch_view_filter("all"))
        self.btn_tab_faces.clicked.connect(lambda: self.switch_view_filter("faces"))
        self.btn_tab_installed.clicked.connect(lambda: self.switch_view_filter("installed"))
        self.btn_tab_updates.clicked.connect(lambda: self.switch_view_filter("updates"))
        
        btn_size = int(42 * self.scale)
        self.btn_search_open = QPushButton("🔍")
        self.btn_search_open.setFixedSize(btn_size, btn_size)
        self.btn_search_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search_open.setStyleSheet(f"""
            QPushButton {{ background-color: #2C2C35; color: white; border-radius: {btn_size//2}px; font-size: {int(18 * self.scale)}px; border: none;}}
            QPushButton:hover {{ background-color: #383845; }}
        """)
        self.btn_search_open.clicked.connect(self.open_search_bar)
        normal_layout.addWidget(self.btn_search_open)

        self.search_container = QWidget()
        search_container_layout = QHBoxLayout(self.search_container)
        search_container_layout.setContentsMargins(0, 0, 0, 0)
        search_container_layout.addStretch() 
        
        self.search_pill = QFrame()
        self.search_pill.setStyleSheet("""
            QFrame { background-color: #22222B; border: 2px solid #5A8DEF; border-radius: 27px; }
        """)
        pill_layout = QHBoxLayout(self.search_pill)
        pill_layout.setContentsMargins(10, 4, 15, 4)
        pill_layout.setSpacing(10)

        self.btn_search_back = QPushButton("←")
        self.btn_search_back.setFixedSize(int(38 * self.scale), int(38 * self.scale))
        self.btn_search_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search_back.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: white; border-radius: 19px; font-size: {int(20 * self.scale)}px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,15); }}
        """)
        self.btn_search_back.clicked.connect(self.close_search_bar)
        pill_layout.addWidget(self.btn_search_back)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search apps, categories, authors...")
        self.search_bar.setFont(QFont("Google Sans", int(16 * self.scale)))
        self.search_bar.setStyleSheet("""
            QLineEdit { background: transparent; color: white; border: none; padding-left: 5px; }
        """)
        self.search_bar.textChanged.connect(self.on_search_query_changed)
        pill_layout.addWidget(self.search_bar, stretch=1)

        self.btn_search_clear = QPushButton("✕")
        self.btn_search_clear.setFixedSize(int(34 * self.scale), int(34 * self.scale))
        self.btn_search_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search_clear.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: #AAAAAA; border-radius: 17px; font-size: {int(16 * self.scale)}px; border: none; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,15); color: white; }}
        """)
        self.btn_search_clear.clicked.connect(self.search_bar.clear)
        pill_layout.addWidget(self.btn_search_clear)

        search_container_layout.addWidget(self.search_pill)

        self.header_stack.addWidget(header_normal)
        self.header_stack.addWidget(self.search_container)
        layout.addWidget(self.header_stack)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1C1C22; border: none; } QProgressBar::chunk { background: #5A8DEF; }")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.page_stack = QStackedWidget()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(int(14 * self.scale))
        self.scroll_area.setWidget(self.list_container)
        
        self.details_section = AppDetailsSection(
            on_back_callback=lambda: self.transition_to(0),
            install_callback=self.start_install,
            on_screenshot_click=self.show_fullscreen_screenshot
        )
        
        self.page_stack.addWidget(self.scroll_area)
        self.page_stack.addWidget(self.details_section)
        layout.addWidget(self.page_stack)

        self.fade_overlay = FadeOverlay(self)

        self.current_filter = "all"
        self.setup_fullscreen_overlay()
        self.load_catalog()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fullscreen_view'):
            self.fullscreen_view.setGeometry(self.rect())
        if hasattr(self, 'fade_overlay'):
            self.fade_overlay.setGeometry(self.page_stack.geometry())

    def open_search_bar(self):
        self.header_stack.setCurrentIndex(1)
        self.search_pill.setMinimumWidth(int(42 * self.scale))
        self.search_pill.setMaximumWidth(int(42 * self.scale))
        
        self.search_anim = QPropertyAnimation(self.search_pill, b"maximumWidth")
        self.search_anim.setDuration(250)
        self.search_anim.setStartValue(int(42 * self.scale))
        self.search_anim.setEndValue(3000) 
        self.search_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.search_anim.finished.connect(lambda: self.search_pill.setMinimumWidth(0))
        self.search_anim.start()
        self.search_bar.setFocus()

    def close_search_bar(self):
        self.search_bar.clear()
        self.search_anim = QPropertyAnimation(self.search_pill, b"maximumWidth")
        self.search_anim.setDuration(200)
        self.search_anim.setStartValue(self.search_pill.width())
        self.search_anim.setEndValue(int(42 * self.scale))
        self.search_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.search_anim.finished.connect(lambda: self.header_stack.setCurrentIndex(0))
        self.search_anim.start()

    def on_search_query_changed(self, text):
        if hasattr(self, 'search_debounce_timer'):
            self.search_debounce_timer.stop()
        else:
            self.search_debounce_timer = QTimer(self)
            self.search_debounce_timer.setSingleShot(True)
            self.search_debounce_timer.timeout.connect(lambda: self.populate_catalog(self.full_catalog_cache))
            
        self.search_debounce_timer.start(300)

    def _update_tab_styles(self, filter_mode):
        self.btn_tab_all.setStyleSheet(self.tab_active_css if filter_mode == "all" else self.tab_inactive_css)
        self.btn_tab_faces.setStyleSheet(self.tab_active_css if filter_mode == "faces" else self.tab_inactive_css)
        self.btn_tab_installed.setStyleSheet(self.tab_active_css if filter_mode == "installed" else self.tab_inactive_css)
        self.btn_tab_updates.setStyleSheet(self.tab_active_css if filter_mode == "updates" else self.tab_inactive_css)

    def transition_to(self, target_index, filter_mode=None):
        if self.page_stack.currentIndex() == target_index and (filter_mode is None or filter_mode == self.current_filter):
            return
            
        if not self.isVisible():
            self.page_stack.setCurrentIndex(target_index)
            if filter_mode:
                self.current_filter = filter_mode
                self._update_tab_styles(filter_mode)
                self.populate_catalog(self.full_catalog_cache)
            return

        self.target_index = target_index
        self.target_filter = filter_mode
        
        self.fade_overlay.setGeometry(self.page_stack.geometry())
        self.fade_overlay.show()
        self.fade_overlay.raise_()
        
        self.fade_anim = QPropertyAnimation(self.fade_overlay, b"alpha")
        self.fade_anim.setDuration(150)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(255)
        self.fade_anim.finished.connect(self._on_transition_midpoint)
        self.fade_anim.start()

    def _on_transition_midpoint(self):
        try:
            self.fade_anim.finished.disconnect(self._on_transition_midpoint)
        except Exception:
            pass
            
        self.page_stack.setCurrentIndex(self.target_index)
        if self.target_filter:
            self.current_filter = self.target_filter
            self._update_tab_styles(self.target_filter)
            self.populate_catalog(self.full_catalog_cache)
            
        self.fade_anim = QPropertyAnimation(self.fade_overlay, b"alpha")
        self.fade_anim.setDuration(150)
        self.fade_anim.setStartValue(255)
        self.fade_anim.setEndValue(0)
        self.fade_anim.finished.connect(self.fade_overlay.hide)
        self.fade_anim.start()

    def switch_view_filter(self, filter_mode):
        self.transition_to(0, filter_mode=filter_mode)

    def setup_fullscreen_overlay(self):
        self.fullscreen_view = QFrame(self)
        self.fullscreen_view.setStyleSheet("background-color: rgba(0, 0, 0, 240);")
        self.fullscreen_view.hide()
        
        fs_layout = QVBoxLayout(self.fullscreen_view)
        fs_layout.setContentsMargins(20, 20, 20, 20)
        
        btn_close_fs = QPushButton("✕")
        btn_close_fs.setFixedSize(50, 50)
        btn_close_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_fs.setStyleSheet("background-color: rgba(255,255,255,20); color: white; border-radius: 25px; font-size: 24px; font-weight: bold; border: none;")
        btn_close_fs.clicked.connect(self.hide_fullscreen)
        
        top_fs = QHBoxLayout()
        top_fs.addStretch()
        top_fs.addWidget(btn_close_fs)
        
        self.fs_image = QLabel()
        self.fs_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fs_image.setStyleSheet("background: transparent;")
        
        fs_layout.addLayout(top_fs)
        fs_layout.addWidget(self.fs_image, stretch=1)
            
    def show_fullscreen_screenshot(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.width() - 80, self.height() - 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.fs_image.setPixmap(scaled)
        self.fullscreen_view.raise_()
        self.fullscreen_view.show()
        
    def hide_fullscreen(self):
        self.fullscreen_view.hide()

    def load_catalog(self):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        lbl_loading = QLabel("Fetching apps from GitHub repository...")
        lbl_loading.setFont(QFont("Google Sans", int(16 * self.scale)))
        lbl_loading.setStyleSheet("color: #888888; margin-top: 50px;")
        lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_loading)

        fetcher = FetchManifestThread()
        self._active_threads.add(fetcher)
        
        def cleanup(apps=None, err=None, t=fetcher):
            self._active_threads.discard(t)
            
        fetcher.on_success.connect(self.cache_and_populate)
        fetcher.on_success.connect(cleanup)
        fetcher.on_error.connect(self.show_error)
        fetcher.on_error.connect(cleanup)
        fetcher.start()

    def cache_and_populate(self, apps_list):
        self.full_catalog_cache = apps_list
        self.populate_catalog(apps_list)

    def populate_catalog(self, apps_list):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        if not apps_list:
            lbl_empty = QLabel("No apps found in the repository manifest.")
            lbl_empty.setStyleSheet(f"color: #AAAAAA; font-size: {int(16 * self.scale)}px;")
            self.list_layout.addWidget(lbl_empty)
            return

        query = self.search_bar.text().lower()
        visible_cards = 0

        for app_data in apps_list:
            if query:
                search_text = f"{app_data.get('name','')} {app_data.get('author','')} {app_data.get('category','')} {app_data.get('description','')} {app_data.get('expanded_description','')}".lower()
                if query not in search_text:
                    continue

            is_face = app_data.get('type') == 'clockface'
            
            if self.current_filter == "all" and is_face: continue
            if self.current_filter == "faces" and not is_face: continue

            card = AppCard(app_data, self.start_install, self.open_app_profile_details)
            
            if self.current_filter == "installed" and not card.is_installed:
                card.setParent(None)
                continue
            if self.current_filter == "updates" and not card.needs_update:
                card.setParent(None)
                continue
                
            self.list_layout.addWidget(card)
            visible_cards += 1

        if visible_cards == 0:
            if query:
                msg = f"No apps matching '{query}'."
            else:
                msg = "No installed applications found." if self.current_filter == "installed" else "All your applications are fully up to date! ✨"
                
            lbl_empty = QLabel(msg)
            lbl_empty.setFont(QFont("Google Sans", int(16 * self.scale)))
            lbl_empty.setStyleSheet("color: #666670; margin-top: 60px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl_empty)

    def open_app_profile_details(self, app_data, card_reference):
        self.details_section.populate_details(app_data, card_reference)
        self.transition_to(1)

    def show_error(self, error_msg):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)
        
        lbl_err = QLabel(f"Failed to connect to GitHub Repo:\n{error_msg}")
        lbl_err.setFont(QFont("Google Sans", int(16 * self.scale)))
        lbl_err.setStyleSheet("color: #E24A4A;")
        lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_err)

    def start_install(self, app_data, card_reference):
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        downloader = DownloadAppThread(app_data)
        self._active_threads.add(downloader)
        
        def cleanup(name=None, err=None, t=downloader):
            self._active_threads.discard(t)
            
        downloader.on_progress.connect(self.progress_bar.setValue)
        downloader.on_finished.connect(lambda name: self.on_install_complete(app_data, card_reference))
        downloader.on_finished.connect(cleanup)
        downloader.on_error.connect(self.on_install_error)
        downloader.on_error.connect(cleanup)
        downloader.start()

    def on_install_complete(self, app_data, card):
        self.progress_bar.hide()
        
        card.is_installed = True
        card.needs_update = False
        card.btn_install.setEnabled(True)
        card.update_button_style()
        
        if self.page_stack.currentIndex() == 1:
            self.details_section.update_action_button_style()

        if self.on_install_success:
            self.on_install_success()
            
        if app_data.get("type") == "clockface":
            main_win = self.window()
            if hasattr(main_win, 'selector_overlay'):
                main_win.selector_overlay.reload_custom_clockfaces()
        if hasattr(self.window(), 'show_toast'):
            icon = app_data.get("icon_url", "✅")
            if app_data.get("type", "app") == "clockface":
                self.window().show_toast("App Store", "App Installed", f"{app_data['name']} is now in your Clockfaces menu.", icon)
            else:
                self.window().show_toast("App Store", "App Installed", f"{app_data['name']} v{app_data['version']} installed!", icon)
            
            # Immediately rebuild the app drawer so the newly installed app appears!
            if hasattr(self.window(), 'rebuild_app_drawer'):
                self.window().rebuild_app_drawer()
        if self.current_filter != "all" or self.search_bar.text():
            self.populate_catalog(self.full_catalog_cache)

    def on_install_error(self, err_msg):
        self.progress_bar.hide()
        QMessageBox.warning(self, "Download Error", err_msg)
        self.load_catalog()