import os
import ssl
import urllib.request
import json
import time  
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor, QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QProgressBar, QMessageBox, QScroller, QStackedWidget, QGridLayout, QGraphicsOpacityEffect, QLineEdit
)

# Raw GitHub URL of your store manifest
MANIFEST_URL = "https://raw.githubusercontent.com/dobmen/gemappkiosstor/main/store_manifest.json"


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

            failed_url = script_url
            os.makedirs("apps", exist_ok=True)
            temp_script = os.path.join("apps", "update.tmp")
            
            req_script = urllib.request.Request(script_url, headers={'User-Agent': 'KioskOS'})
            with urllib.request.urlopen(req_script, timeout=10, context=ctx) as response:
                with open(temp_script, 'wb') as f:
                    f.write(response.read())
                    
            self.on_progress.emit(80)
            
            target_script = os.path.join("apps", self.app_data["filename"])
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
            print(f"Image download exception trace for {self.url}: {e}")


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
        
        self.setMinimumHeight(145)
        self.setStyleSheet("""
            AppCard { background-color: #1C1C22; border: 1px solid #2C2C35; border-radius: 12px; }
            AppCard:hover { background-color: #24242E; border-color: #3C3C45; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        lbl_name = QLabel(f"{app_data['name']} (v{app_data['version']})")
        lbl_name.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white; border: none; background: transparent;")
        
        lbl_author = QLabel(f"By {app_data.get('author', 'Unknown')}")
        lbl_author.setFont(QFont("Google Sans", 12))
        lbl_author.setStyleSheet("color: #888888; border: none; background: transparent;")
        
        lbl_desc = QLabel(app_data['description'])
        lbl_desc.setFont(QFont("Google Sans", 14))
        lbl_desc.setStyleSheet("color: #CCCCCC; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)

        info_layout.addWidget(lbl_name)
        info_layout.addWidget(lbl_author)
        info_layout.addWidget(lbl_desc)

        local_script = os.path.join("apps", app_data["filename"])
        ver_path = local_script.replace(".py", ".ver")
        
        self.is_installed = os.path.exists(local_script)
        installed_version = "0.0.0"
        if os.path.exists(ver_path):
            with open(ver_path, "r") as f:
                installed_version = f.read().strip()
        
        self.needs_update = self.is_installed and (str(app_data["version"]) > installed_version)

        self.btn_install = QPushButton()
        self.btn_install.setFixedSize(130, 45)
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button_style()
        self.btn_install.clicked.connect(self.on_install_click)

        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.btn_install, alignment=Qt.AlignmentFlag.AlignVCenter)

    def update_button_style(self):
        if self.needs_update:
            self.btn_install.setText("⬆ Update")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #F39C12; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; border: none; }
                QPushButton:hover { background-color: #E67E22; }
            """)
        elif self.is_installed:
            self.btn_install.setText("Installed")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #2E2E38; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: 15px; border: none; }
                QPushButton:hover { background-color: #383845; color: white; }
            """)
        else:
            self.btn_install.setText("⬇ Install")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; border: none; }
                QPushButton:hover { background-color: #4A7DDF; }
            """)

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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(15)

        nav_layout = QHBoxLayout()
        btn_back = QPushButton("◀ Catalog")
        btn_back.setFixedSize(110, 36)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 8px; font-weight: bold; border: none;")
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
        self.content_layout.setSpacing(25)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.identity_card = QFrame()
        self.identity_card.setStyleSheet("background-color: #1C1C22; border: 1px solid #2C2C35; border-radius: 16px;")
        id_layout = QHBoxLayout(self.identity_card)
        id_layout.setContentsMargins(20, 20, 20, 20)
        id_layout.setSpacing(20)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(80, 80)
        self.lbl_icon.setStyleSheet("background-color: #2C2C35; border-radius: 40px;")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.lbl_name = QLabel()
        self.lbl_name.setFont(QFont("Google Sans", 22, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: white; border: none;")
        
        self.lbl_author_cat = QLabel()
        self.lbl_author_cat.setFont(QFont("Google Sans", 13))
        self.lbl_author_cat.setStyleSheet("color: #888888; border: none;")
        title_box.addWidget(self.lbl_name)
        title_box.addWidget(self.lbl_author_cat)

        self.btn_action = QPushButton()
        self.btn_action.setFixedSize(140, 48)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.clicked.connect(self.on_action_clicked)

        id_layout.addWidget(self.lbl_icon)
        id_layout.addLayout(title_box, stretch=1)
        id_layout.addWidget(self.btn_action)
        self.content_layout.addWidget(self.identity_card)

        self.scr_scroll = QScrollArea()
        self.scr_scroll.setFixedHeight(170)
        self.scr_scroll.setWidgetResizable(True)
        self.scr_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scr_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.scr_container = QWidget()
        self.scr_layout = QHBoxLayout(self.scr_container)
        self.scr_layout.setContentsMargins(0, 0, 0, 0)
        self.scr_layout.setSpacing(14)
        self.scr_scroll.setWidget(self.scr_container)
        self.content_layout.addWidget(self.scr_scroll)

        self.lbl_desc_title = QLabel("About this application")
        self.lbl_desc_title.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        self.lbl_desc = QLabel()
        self.lbl_desc.setFont(QFont("Google Sans", 14))
        self.lbl_desc.setStyleSheet("color: #CCCCCC; line-height: 22px;")
        self.lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_desc_title)
        self.content_layout.addWidget(self.lbl_desc)

        self.spec_card = QFrame()
        self.spec_card.setStyleSheet("background-color: #14141A; border-radius: 12px; border: 1px solid #22222A;")
        spec_layout = QGridLayout(self.spec_card)
        spec_layout.setContentsMargins(20, 15, 20, 15)
        spec_layout.setSpacing(15)

        self.lbl_meta_ver_title = QLabel("Version")
        self.lbl_meta_ver_title.setStyleSheet("color: #666670; font-size: 13px; font-weight: bold; border: none;")
        self.lbl_meta_ver = QLabel()
        self.lbl_meta_ver.setStyleSheet("color: white; font-size: 14px; border: none;")
        
        self.lbl_meta_size_title = QLabel("Storage Needed")
        self.lbl_meta_size_title.setStyleSheet("color: #666670; font-size: 13px; font-weight: bold; border: none;")
        self.lbl_meta_size = QLabel()
        self.lbl_meta_size.setStyleSheet("color: white; font-size: 14px; border: none;")

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
        self.lbl_author_cat.setText(f"By {app_data.get('author', 'Unknown')} • {app_data.get('category', 'Utility')}")
        
        desc_text = app_data.get('expanded_description') or app_data.get('description', '')
        self.lbl_desc.setText(desc_text)
        
        self.lbl_meta_ver.setText(str(app_data['version']))
        self.lbl_meta_size.setText(app_data.get('storage_needed', 'Unknown Size'))

        icon_pix = QPixmap(80, 80)
        icon_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(icon_pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#5A8DEF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 80, 80)
        p.setPen(QColor("white"))
        p.setFont(QFont("Google Sans", 26, QFont.Weight.Bold))
        p.drawText(QRect(0, 0, 80, 80), Qt.AlignmentFlag.AlignCenter, app_data['name'][0].upper())
        p.end()
        self.lbl_icon.setPixmap(icon_pix)

        if app_data.get('icon_url'):
            icon_thread = NetworkImageThread(app_data['icon_url'], self.lbl_icon, 80, 80, radius=40)
            icon_thread.on_image_ready.connect(self.apply_downloaded_image)
            icon_thread.start()
            self.active_threads.append(icon_thread)

        for i in reversed(range(self.scr_layout.count())):
            self.scr_layout.itemAt(i).widget().setParent(None)

        screenshots = app_data.get('screenshots', [])
        if screenshots:
            self.scr_scroll.show()
            for s_url in screenshots:
                scr_lbl = ClickableScreenshot()
                scr_lbl.clicked.connect(self.on_screenshot_click)
                scr_lbl.setFixedSize(240, 140)
                scr_lbl.setStyleSheet("background-color: #2C2C35; border-radius: 8px; border: 1px solid #3C3C45;")
                scr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.scr_layout.addWidget(scr_lbl)
                
                scr_thread = NetworkImageThread(s_url, scr_lbl, 240, 140, radius=8)
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
            self.btn_action.setStyleSheet("background-color: #F39C12; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; border: none;")
        elif self.active_card.is_installed:
            self.btn_action.setText("Installed")
            self.btn_action.setStyleSheet("background-color: #2E2E38; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: 15px; border: none;")
        else:
            self.btn_action.setText("⬇ Install")
            self.btn_action.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; border: none;")

    def on_action_clicked(self):
        self.btn_action.setEnabled(False)
        self.btn_action.setText("Processing...")
        self.install_callback(self.app_data, self.active_card)


class AppStorePage(QWidget):
    def __init__(self, on_install_success=None):
        super().__init__()
        self.on_install_success = on_install_success
        self.full_catalog_cache = []
        self.base_pos = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("GitHub App Store")
        self.title_lbl.setFont(QFont("Google Sans", 26, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: white;")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()

        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search apps...")
        self.search_bar.setMaximumWidth(0)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #2C2C35;
                color: white;
                border: 1px solid #3C3C45;
                border-radius: 18px;
                padding: 4px 15px;
                font-family: 'Google Sans';
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #5A8DEF; }
        """)
        self.search_bar.textChanged.connect(self.on_search_query_changed)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(36, 36)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton { background: transparent; color: white; border-radius: 18px; font-size: 18px; border: none;}
            QPushButton:hover { background-color: rgba(255,255,255,20); }
        """)
        self.btn_search.clicked.connect(self.toggle_search)

        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.btn_search)
        header_layout.addLayout(search_layout)
        header_layout.addSpacing(10)

        self.btn_tab_all = QPushButton("Catalog")
        self.btn_tab_installed = QPushButton("Installed")
        self.btn_tab_updates = QPushButton("Need Updating")
        
        self.tab_active_css = "background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: 13px; padding: 6px 14px; border: none;"
        self.tab_inactive_css = "background-color: #2C2C35; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: 13px; padding: 6px 14px; border: none;"
        
        self.btn_tab_all.setStyleSheet(self.tab_active_css)
        self.btn_tab_installed.setStyleSheet(self.tab_inactive_css)
        self.btn_tab_updates.setStyleSheet(self.tab_inactive_css)

        for btn in [self.btn_tab_all, self.btn_tab_installed, self.btn_tab_updates]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            header_layout.addWidget(btn)

        self.btn_tab_all.clicked.connect(lambda: self.switch_view_filter("all"))
        self.btn_tab_installed.clicked.connect(lambda: self.switch_view_filter("installed"))
        self.btn_tab_updates.clicked.connect(lambda: self.switch_view_filter("updates"))
        
        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1C1C22; border: none; } QProgressBar::chunk { background: #5A8DEF; }")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.page_stack = QStackedWidget()
        
        self.page_opacity = QGraphicsOpacityEffect(self.page_stack)
        self.page_stack.setGraphicsEffect(self.page_opacity)
        self.page_opacity.setEnabled(False)  # <-- FIX: Default opacity effect OFF
        
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
        self.list_layout.setSpacing(14)
        self.scroll_area.setWidget(self.list_container)
        
        self.details_section = AppDetailsSection(
            on_back_callback=lambda: self.transition_to(0, slide_dir="right"),
            install_callback=self.start_install,
            on_screenshot_click=self.show_fullscreen_screenshot
        )
        
        self.page_stack.addWidget(self.scroll_area)
        self.page_stack.addWidget(self.details_section)
        layout.addWidget(self.page_stack)

        self.current_filter = "all"
        self.setup_fullscreen_overlay()
        self.load_catalog()

    def toggle_search(self):
        if not hasattr(self, 'search_anim'):
            self.search_anim = QPropertyAnimation(self.search_bar, b"maximumWidth")
            self.search_anim.setDuration(300)
            self.search_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
        self.search_anim.stop()
        try:
            self.search_anim.finished.disconnect()
        except Exception:
            pass

        if self.search_bar.maximumWidth() > 0:
            self.search_anim.setStartValue(self.search_bar.maximumWidth())
            self.search_anim.setEndValue(0)
            self.search_anim.finished.connect(self.search_bar.clear)
        else:
            self.search_anim.setStartValue(0)
            self.search_anim.setEndValue(220)
            self.search_bar.setFocus()
            
        self.search_anim.start()

    def on_search_query_changed(self, text):
        self.populate_catalog(self.full_catalog_cache)

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
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fullscreen_view'):
            self.fullscreen_view.setGeometry(self.rect())
            
    def show_fullscreen_screenshot(self, pixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.width() - 80, self.height() - 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.fs_image.setPixmap(scaled)
        self.fullscreen_view.raise_()
        self.fullscreen_view.show()
        
    def hide_fullscreen(self):
        self.fullscreen_view.hide()

    def _update_tab_styles(self, filter_mode):
        self.btn_tab_all.setStyleSheet(self.tab_active_css if filter_mode == "all" else self.tab_inactive_css)
        self.btn_tab_installed.setStyleSheet(self.tab_active_css if filter_mode == "installed" else self.tab_inactive_css)
        self.btn_tab_updates.setStyleSheet(self.tab_active_css if filter_mode == "updates" else self.tab_inactive_css)

    def transition_to(self, target_index, filter_mode=None, slide_dir="left"):
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
        self.slide_dir = slide_dir
        
        self.page_opacity.setEnabled(True)  # <-- FIX: Enable opacity strictly for the animation
        
        if not hasattr(self, 'out_anim_group') or self.out_anim_group.state() != QPropertyAnimation.State.Running:
            self.base_pos = self.page_stack.pos()
            
        self.out_anim_group = QParallelAnimationGroup()
        
        self.fade_out = QPropertyAnimation(self.page_opacity, b"opacity")
        self.fade_out.setDuration(150)
        self.fade_out.setStartValue(self.page_opacity.opacity())
        self.fade_out.setEndValue(0.0)
        
        self.slide_out = QPropertyAnimation(self.page_stack, b"pos")
        self.slide_out.setDuration(150)
        self.slide_out.setStartValue(self.base_pos)
        offset = QPoint(-40 if slide_dir == "left" else 40, 0)
        self.slide_out.setEndValue(self.base_pos + offset)
        self.slide_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.out_anim_group.addAnimation(self.fade_out)
        self.out_anim_group.addAnimation(self.slide_out)
        self.out_anim_group.finished.connect(self._on_transition_midpoint)
        self.out_anim_group.start()

    def _on_transition_midpoint(self):
        try:
            self.out_anim_group.finished.disconnect(self._on_transition_midpoint)
        except Exception:
            pass
            
        self.page_stack.setCurrentIndex(self.target_index)
        if self.target_filter:
            self.current_filter = self.target_filter
            self._update_tab_styles(self.target_filter)
            self.populate_catalog(self.full_catalog_cache)
            
        self.in_anim_group = QParallelAnimationGroup()
        
        self.fade_in = QPropertyAnimation(self.page_opacity, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        
        self.slide_in = QPropertyAnimation(self.page_stack, b"pos")
        self.slide_in.setDuration(200)
        offset = QPoint(40 if self.slide_dir == "left" else -40, 0)
        self.slide_in.setStartValue(self.base_pos + offset)
        self.slide_in.setEndValue(self.base_pos)
        self.slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.in_anim_group.addAnimation(self.fade_in)
        self.in_anim_group.addAnimation(self.slide_in)
        self.in_anim_group.finished.connect(self._on_transition_finished)
        self.in_anim_group.start()

    def _on_transition_finished(self):
        try:
            self.in_anim_group.finished.disconnect(self._on_transition_finished)
        except Exception:
            pass
        self.page_opacity.setEnabled(False)  # <-- FIX: Disable completely when done

    def switch_view_filter(self, filter_mode):
        tab_indices = {"all": 0, "installed": 1, "updates": 2}
        curr_idx = tab_indices.get(self.current_filter, 0)
        targ_idx = tab_indices.get(filter_mode, 0)
        
        if targ_idx == curr_idx:
            if self.page_stack.currentIndex() == 1:
                self.transition_to(0, filter_mode=filter_mode, slide_dir="right")
            return
            
        slide_dir = "left" if targ_idx > curr_idx else "right"
        self.transition_to(0, filter_mode=filter_mode, slide_dir=slide_dir)

    def load_catalog(self):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        lbl_loading = QLabel("Fetching apps from GitHub repository...")
        lbl_loading.setFont(QFont("Google Sans", 16))
        lbl_loading.setStyleSheet("color: #888888; margin-top: 50px;")
        lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_loading)

        self.fetcher = FetchManifestThread()
        self.fetcher.on_success.connect(self.cache_and_populate)
        self.fetcher.on_error.connect(self.show_error)
        self.fetcher.start()

    def cache_and_populate(self, apps_list):
        self.full_catalog_cache = apps_list
        self.populate_catalog(apps_list)

    def populate_catalog(self, apps_list):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        if not apps_list:
            lbl_empty = QLabel("No apps found in the repository manifest.")
            lbl_empty.setStyleSheet("color: #AAAAAA; font-size: 16px;")
            self.list_layout.addWidget(lbl_empty)
            return

        query = self.search_bar.text().lower()
        visible_cards = 0

        for app_data in apps_list:
            if query:
                search_text = f"{app_data.get('name','')} {app_data.get('author','')} {app_data.get('category','')} {app_data.get('description','')} {app_data.get('expanded_description','')}".lower()
                if query not in search_text:
                    continue

            card = AppCard(app_data, self.start_install, self.open_app_profile_details)
            
            if self.current_filter == "installed" and not card.is_installed:
                card.deleteLater()
                continue
            if self.current_filter == "updates" and not card.needs_update:
                card.deleteLater()
                continue
                
            self.list_layout.addWidget(card)
            visible_cards += 1

        if visible_cards == 0:
            if query:
                msg = f"No apps matching '{query}'."
            else:
                msg = "No installed applications found." if self.current_filter == "installed" else "All your applications are fully up to date! ✨"
                
            lbl_empty = QLabel(msg)
            lbl_empty.setFont(QFont("Google Sans", 16))
            lbl_empty.setStyleSheet("color: #666670; margin-top: 60px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl_empty)

    def open_app_profile_details(self, app_data, card_reference):
        self.details_section.populate_details(app_data, card_reference)
        self.transition_to(1, slide_dir="left")

    def show_error(self, error_msg):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)
        
        lbl_err = QLabel(f"Failed to connect to GitHub Repo:\n{error_msg}")
        lbl_err.setFont(QFont("Google Sans", 16))
        lbl_err.setStyleSheet("color: #E24A4A;")
        lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_err)

    def start_install(self, app_data, card_reference):
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.downloader = DownloadAppThread(app_data)
        self.downloader.on_progress.connect(self.progress_bar.setValue)
        self.downloader.on_finished.connect(lambda name: self.on_install_complete(app_data, card_reference))
        self.downloader.on_error.connect(self.on_install_error)
        self.downloader.start()

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
            
        QMessageBox.information(self, "Success", f"Successfully installed {app_data['name']} v{app_data['version']}!")
        
        if self.current_filter != "all" or self.search_bar.text():
            self.populate_catalog(self.full_catalog_cache)

    def on_install_error(self, err_msg):
        self.progress_bar.hide()
        QMessageBox.warning(self, "Download Error", err_msg)
        self.load_catalog()