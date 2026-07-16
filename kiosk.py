import os
import sys
import json
import ssl
import importlib
import urllib.request
from PyQt6.QtCore import QDate, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QRect, Qt, QTime, QTimer, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QFontDatabase, QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QMainWindow, 
    QPushButton, QSlider, QVBoxLayout, QWidget, QScrollArea, QScroller, QFrame, QSizePolicy, QGraphicsOpacityEffect, QStackedWidget
)

# Import our custom modules
from components import SlidingPanel
from apps.local_music import LocalMusicPage
from apps.web_app import create_web_app_view
from apps.app_store import AppStorePage


class SystemUpdateCheckThread(QThread):
    """Background worker that checks GitHub every 24 hours for new Kiosk OS releases without freezing the GUI."""
    update_detected = pyqtSignal(str)

    def run(self):
        try:
            local_version = "0.1.0"
            if os.path.exists("os_version.json"):
                with open("os_version.json", "r") as f:
                    data = json.load(f)
                    local_version = data.get("version", "0.1.0")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/main/os_version.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-Updater/1.0'})
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                remote_data = json.loads(response.read().decode('utf-8'))
                remote_version = remote_data.get("version", local_version)
                
                if remote_version != local_version:
                    self.update_detected.emit(remote_version)
        except Exception:
            pass


class AppStoreUpdateCheckThread(QThread):
    """Background worker that checks for updates only for locally installed applications to prevent ghost notifications."""
    updates_detected = pyqtSignal(list)

    def run(self):
        try:
            # 1. Identify which apps are genuinely installed locally
            installed_modules = []
            if os.path.exists("apps"):
                for filename in os.listdir("apps"):
                    if filename.endswith(".py") and filename not in ["__init__.py", "app_store.py", "local_music.py", "web_app.py", "settings.py"]:
                        installed_modules.append(filename.replace(".py", ""))

            if not installed_modules:
                return

            # 2. Get local app version configurations
            local_versions = {}
            if os.path.exists("apps_version.json"):
                with open("apps_version.json", "r") as f:
                    local_versions = json.load(f)

            # 3. Check remote repository versions mapping
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/main/apps_version.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-AppUpdater/1.0'})
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                remote_versions = json.loads(response.read().decode('utf-8'))
                
                apps_needing_update = []
                for app_id in installed_modules:
                    if app_id in remote_versions:
                        current_v = local_versions.get(app_id, "0.1.0")
                        remote_v = remote_versions[app_id]
                        if remote_v != current_v:
                            clean_name = app_id.replace("_", " ").title()
                            apps_needing_update.append(clean_name)
                            
                if apps_needing_update:
                    self.updates_detected.emit(apps_needing_update)
        except Exception:
            pass


class ToastNotification(QFrame):
    """A One UI style system-wide heads-up notification pop-up."""
    def __init__(self, parent, app_name, title, desc, icon_char, click_callback):
        super().__init__(parent)
        self.app_name = app_name
        self.click_callback = click_callback
        
        self.setFixedSize(420, 85)
        self.setStyleSheet("background-color: #22222B; border-radius: 42px; border: 1px solid #33333F;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 25, 10)
        layout.setSpacing(15)
        
        lbl_icon = QLabel(icon_char)
        lbl_icon.setFont(QFont("Google Sans", 24))
        lbl_icon.setFixedSize(54, 54)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("background-color: rgba(255,255,255,10); border-radius: 27px; border: none;")
        
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Google Sans", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        
        clean_desc = desc if len(desc) <= 35 else desc[:32] + "..."
        lbl_desc = QLabel(clean_desc)
        lbl_desc.setFont(QFont("Google Sans", 13))
        lbl_desc.setStyleSheet("color: #AAAAAA; border: none; background: transparent;")
        
        text_box.addWidget(lbl_title)
        text_box.addWidget(lbl_desc)
        
        layout.addWidget(lbl_icon)
        layout.addLayout(text_box, stretch=1)
        
        self.pos_anim = QPropertyAnimation(self, b"pos")
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.pos_anim.setDuration(450)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.dismiss)
        self.hide_timer.setSingleShot(True)
        
    def show_toast(self):
        self.raise_()
        self.show()
        self.pos_anim.setStartValue(QPoint(302, -100))
        self.pos_anim.setEndValue(QPoint(302, 25))
        self.pos_anim.start()
        self.hide_timer.start(4000)
        
    def dismiss(self):
        self.pos_anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.pos_anim.setStartValue(self.pos())
        self.pos_anim.setEndValue(QPoint(302, -100))
        self.pos_anim.finished.connect(self.deleteLater)
        self.pos_anim.start()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_timer.stop()
            self.dismiss()
            if self.click_callback and self.app_name:
                self.click_callback(self.app_name)


class DynamicAppButton(QFrame):
    def __init__(self, name, icon_path, callback, scale=100, layout_type="grid"):
        super().__init__()
        self.name = name
        self.callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            DynamicAppButton { background-color: transparent; border-radius: 16px; }
            DynamicAppButton:hover { background-color: rgba(255, 255, 255, 12); }
        """)

        base_icon_size = 72
        base_font_size = 14
        
        icon_size = int(base_icon_size * (scale / 100.0))
        font_size = max(9, int(base_font_size * (scale / 100.0)))

        lbl_icon = QLabel()
        lbl_icon.setFixedSize(icon_size, icon_size)
        lbl_icon.setStyleSheet("background: transparent;")
        
        target_pix = QPixmap(icon_size, icon_size)
        target_pix.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter()
        try:
            painter.begin(target_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            original_pix = QPixmap()
            if os.path.exists(icon_path):
                original_pix = QPixmap(icon_path)
            elif os.path.exists("icons/prototype.png"):
                original_pix = QPixmap("icons/prototype.png")
            elif os.path.exists("icons/prototype.svg"):
                original_pix = QPixmap("icons/prototype.svg")
                
            if not original_pix.isNull():
                path = QPainterPath()
                path.addEllipse(0, 0, icon_size, icon_size)
                painter.setClipPath(path)
                
                scaled_pix = original_pix.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                if not scaled_pix.isNull():
                    x = (icon_size - scaled_pix.width()) // 2
                    y = (icon_size - scaled_pix.height()) // 2
                    painter.drawPixmap(x, y, scaled_pix)
            else:
                colors = ["#E24A4A", "#5A8DEF", "#F39C12", "#27AE60", "#8E44AD", "#9B59B6"]
                color_idx = len(name) % len(colors)
                
                painter.setBrush(QColor(colors[color_idx]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(0, 0, icon_size, icon_size)
                
                painter.setPen(QColor("#FFFFFF"))
                safe_font_size = max(1, int(icon_size * 0.45))
                painter.setFont(QFont("Google Sans", safe_font_size, QFont.Weight.Bold))
                first_letter = name[0].upper() if name else "?"
                painter.drawText(QRect(0, 0, icon_size, icon_size), Qt.AlignmentFlag.AlignCenter, first_letter)
        finally:
            if painter.isActive():
                painter.end()
                
        lbl_icon.setPixmap(target_pix)
        
        lbl_text = QLabel(name)
        lbl_text.setFont(QFont("Google Sans", font_size, QFont.Weight.Bold))
        lbl_text.setStyleSheet("color: white; background: transparent;")

        if layout_type == "grid":
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            layout = QVBoxLayout(self)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            layout.setContentsMargins(10, 15, 10, 10) 
            layout.setSpacing(12) 
            
            box_width = int(icon_size * 2) 
            box_height = int(icon_size + (font_size * 4.5) + 40)
            self.setFixedSize(box_width, box_height) 
            
            lbl_text.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            lbl_text.setWordWrap(True)
            
            layout.addWidget(lbl_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(lbl_text, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout = QHBoxLayout(self)
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.setContentsMargins(30, 15, 30, 15)
            layout.setSpacing(25)
            self.setFixedHeight(icon_size + 40)
            
            layout.addWidget(lbl_icon)
            layout.addWidget(lbl_text)
            layout.addStretch() 

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.name)


class NestKiosk(QMainWindow):
    def __init__(self):
        super().__init__()
        
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        if os.path.exists(font_dir):
            for filename in os.listdir(font_dir):
                if filename.endswith(".ttf") or filename.endswith(".otf"):
                    QFontDatabase.addApplicationFont(os.path.join(font_dir, filename))

        app_font = QFont("Google Sans")
        QApplication.setFont(app_font)
        
        self.setFixedSize(1024, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #0C0C0E; color: #FFFFFF;")

        self.drag_start_pos = None
        self.active_gesture = None  
        self.running_apps = {} 
        self.current_toast = None
        self.empty_label = None

        # -------------------------------------------------------------
        # 1. MAIN SCREEN CAROUSEL
        # -------------------------------------------------------------
        self.main_carousel = QWidget(self)
        self.main_carousel.setGeometry(0, 0, 1024, 600)

        self.home_index = 0
        self.home_pages = []
        
        self.page_clock = QWidget(self.main_carousel)
        self.page_clock.setGeometry(0, 0, 1024, 600)
        clock_layout = QVBoxLayout(self.page_clock)
        clock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time = QLabel()
        self.lbl_time.setFont(QFont("Google Sans", 95, QFont.Weight.Bold))
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date = QLabel()
        self.lbl_date.setFont(QFont("Google Sans", 24))
        self.lbl_date.setStyleSheet("color: #888888;")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.lbl_time)
        clock_layout.addWidget(self.lbl_date)
        
        self.page_media = QWidget(self.main_carousel)
        self.page_media.setGeometry(1024, 0, 1024, 600)
        media_layout = QVBoxLayout(self.page_media)
        media_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_media_title = QLabel("Now Playing")
        lbl_media_title.setFont(QFont("Google Sans", 32, QFont.Weight.Bold))
        lbl_media_track = QLabel("No active stream • Swipe up to launch Spotify")
        lbl_media_track.setStyleSheet("color: #AAAAAA; font-size: 18px; margin-top: 10px;")
        media_layout.addWidget(lbl_media_title, alignment=Qt.AlignmentFlag.AlignCenter)
        media_layout.addWidget(lbl_media_track, alignment=Qt.AlignmentFlag.AlignCenter)

        self.home_pages.extend([self.page_clock, self.page_media])

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        self.indicator = QLabel("▲ Swipe up for apps", self)
        self.indicator.setGeometry(0, 560, 1024, 40)
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indicator.setStyleSheet("color: #444444; font-size: 14px; font-weight: bold;")

        # -------------------------------------------------------------
        # 2. CONTROL CENTER
        # -------------------------------------------------------------
        self.control_center = SlidingPanel(self, QRect(0, -500, 1024, 500), QRect(0, 0, 1024, 500))
        self.control_center.setStyleSheet("background-color: #16161A; border-bottom: 2px solid #282830;")
        
        self.cc_header = QWidget(self.control_center)
        self.cc_header.setGeometry(0, 0, 1024, 60)
        self.cc_header.setStyleSheet("background-color: rgba(22, 22, 26, 240); border-bottom: 1px solid #22222A;")
        
        header_layout = QHBoxLayout(self.cc_header)
        header_layout.setContentsMargins(50, 10, 50, 10)
        
        self.btn_tab_settings = QPushButton("⚙️ Quick Settings")
        self.btn_tab_notifs = QPushButton("🔔 Notifications")
        
        self.cc_tab_active = "background: rgba(255,255,255,30); color: white; border-radius: 18px; font-weight: bold; font-size: 15px; padding: 6px 20px;"
        self.cc_tab_inactive = "background: transparent; color: rgba(255,255,255,140); border-radius: 18px; font-weight: bold; font-size: 15px; padding: 6px 20px;"
        
        self.btn_tab_settings.setStyleSheet(self.cc_tab_active)
        self.btn_tab_notifs.setStyleSheet(self.cc_tab_inactive)
        self.btn_tab_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_tab_settings.clicked.connect(lambda: self.switch_cc_page(0))
        self.btn_tab_notifs.clicked.connect(lambda: self.switch_cc_page(1))
        
        header_layout.addStretch()
        header_layout.addWidget(self.btn_tab_settings)
        header_layout.addWidget(self.btn_tab_notifs)
        header_layout.addStretch()

        self.cc_carousel = QWidget(self.control_center)
        self.cc_carousel.setGeometry(0, 60, 1024, 440)
        self.cc_index = 0
        self.cc_pages = []

        # Page 0: Quick Settings
        self.page_settings = QWidget(self.cc_carousel)
        self.page_settings.setGeometry(0, 0, 1024, 440)
        settings_layout = QVBoxLayout(self.page_settings)
        settings_layout.setContentsMargins(60, 20, 60, 20)
        settings_layout.setSpacing(20)

        qs_card = QFrame()
        qs_card.setStyleSheet("background-color: #22222B; border-radius: 12px; border: 1px solid #2F2F3B;")
        qs_card_layout = QVBoxLayout(qs_card)
        qs_card_layout.setContentsMargins(20, 20, 20, 20)

        slider_layout = QGridLayout()
        slider_layout.setSpacing(20)
        
        lbl_b = QLabel("☀️ Brightness")
        lbl_b.setStyleSheet("background: transparent; border: none;")
        slider_layout.addWidget(lbl_b, 0, 0)
        b_slider = QSlider(Qt.Orientation.Horizontal)
        b_slider.setValue(80)
        slider_layout.addWidget(b_slider, 0, 1)

        lbl_v = QLabel("🔊 Volume")
        lbl_v.setStyleSheet("background: transparent; border: none;")
        slider_layout.addWidget(lbl_v, 1, 0)
        v_slider = QSlider(Qt.Orientation.Horizontal)
        v_slider.setValue(50)
        slider_layout.addWidget(v_slider, 1, 1)
        
        qs_card_layout.addLayout(slider_layout)
        settings_layout.addWidget(qs_card)
        settings_layout.addStretch()

        close_sys_btn = QPushButton("✕ Exit Kiosk OS")
        close_sys_btn.setFixedHeight(48)
        close_sys_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_sys_btn.setStyleSheet("background-color: #E24A4A; color: white; border-radius: 10px; font-size: 16px; font-weight: bold;")
        close_sys_btn.clicked.connect(self.close)
        settings_layout.addWidget(close_sys_btn)

        # Page 1: Notification Center
        self.page_notifs = QWidget(self.cc_carousel)
        self.page_notifs.setGeometry(1024, 0, 1024, 440)
        notifs_main_layout = QVBoxLayout(self.page_notifs)
        notifs_main_layout.setContentsMargins(50, 15, 50, 15)
        notifs_main_layout.setSpacing(10)

        notif_header = QHBoxLayout()
        self.lbl_notif_count = QLabel("Recent Alerts")
        self.lbl_notif_count.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        notif_header.addWidget(self.lbl_notif_count)
        notif_header.addStretch()

        btn_clear_notifs = QPushButton("Clear All")
        btn_clear_notifs.setFixedSize(100, 32)
        btn_clear_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_notifs.setStyleSheet("background: rgba(255,255,255,15); color: white; border-radius: 6px; font-weight: bold;")
        btn_clear_notifs.clicked.connect(self.clear_all_notifications)
        notif_header.addWidget(btn_clear_notifs)
        notifs_main_layout.addLayout(notif_header)

        self.notif_scroll = QScrollArea()
        self.notif_scroll.setWidgetResizable(True)
        self.notif_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.notif_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notif_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.notif_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.notif_container = QWidget()
        self.notif_container.setStyleSheet("background: transparent;")
        self.notif_layout = QVBoxLayout(self.notif_container)
        self.notif_layout.setContentsMargins(0, 0, 0, 10)
        self.notif_layout.setSpacing(12)
        self.notif_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.notif_scroll.setWidget(self.notif_container)
        notifs_main_layout.addWidget(self.notif_scroll)

        self.cc_pages.extend([self.page_settings, self.page_notifs])
        
        # Completely empty tray at initial execution
        self.update_notif_header()

        # -------------------------------------------------------------
        # 3. RESPONSIVE APP DRAWER
        # -------------------------------------------------------------
        self.app_drawer = SlidingPanel(self, QRect(0, 600, 1024, 600), QRect(0, 0, 1024, 600))
        self.app_drawer.setStyleSheet("background-color: #121215;")
        
        drawer_main_layout = QVBoxLayout(self.app_drawer)
        drawer_main_layout.setContentsMargins(0, 30, 0, 0)
        drawer_main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(60, 0, 60, 0)
        
        drawer_title = QLabel("Applications")
        drawer_title.setFont(QFont("Google Sans", 26, QFont.Weight.Bold))
        header_layout.addWidget(drawer_title)
        header_layout.addStretch()

        self.multitask_btn_container = QWidget()
        self.multitask_btn_container.setFixedSize(170, 48)
        self.multitask_btn_container.setStyleSheet("background: transparent;")

        self.btn_multitask = QPushButton("🗂️ Active Tasks", self.multitask_btn_container)
        self.btn_multitask.setGeometry(0, 4, 160, 40)
        self.btn_multitask.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_multitask.setFont(QFont("Google Sans", 13, QFont.Weight.Bold))
        self.btn_multitask.setStyleSheet("""
            QPushButton { background-color: #22222A; color: white; border: 1px solid #33333F; border-radius: 20px; }
            QPushButton:hover { background-color: #2E2E38; border-color: #4A4A5A; }
        """)
        self.btn_multitask.clicked.connect(self.toggle_task_ribbon)

        self.lbl_task_badge = QLabel("0", self.multitask_btn_container)
        self.lbl_task_badge.setGeometry(142, 0, 24, 24)
        self.lbl_task_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_task_badge.setFont(QFont("Google Sans", 11, QFont.Weight.Bold))
        self.lbl_task_badge.setStyleSheet("""
            background-color: #3EA6FF; color: #0E0E12; border-radius: 12px; border: 2px solid #121215; font-weight: bold;
        """)
        self.lbl_task_badge.hide() 

        header_layout.addWidget(self.multitask_btn_container)
        drawer_main_layout.addLayout(header_layout)

        self.task_ribbon = QFrame()
        self.task_ribbon.setFixedHeight(120)
        self.task_ribbon.setStyleSheet("background-color: #1A1A22; border-top: 1px solid #2A2A35; border-bottom: 1px solid #2A2A35;")
        self.task_ribbon.hide()
        
        self.ribbon_layout = QHBoxLayout(self.task_ribbon)
        self.ribbon_layout.setContentsMargins(60, 15, 60, 15)
        self.ribbon_layout.setSpacing(15)
        self.ribbon_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        drawer_main_layout.addWidget(self.task_ribbon)

        self.drawer_scroll = QScrollArea()
        self.drawer_scroll.setWidgetResizable(True)
        self.drawer_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.drawer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.drawer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.drawer_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.drawer_container = QWidget()
        self.drawer_container.setStyleSheet("background: transparent;")
        
        self.drawer_grid = QGridLayout(self.drawer_container)
        self.drawer_grid.setContentsMargins(60, 20, 60, 100) 
        self.drawer_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.drawer_scroll.setWidget(self.drawer_container)
        drawer_main_layout.addWidget(self.drawer_scroll)

        self.rebuild_app_drawer()

        # -------------------------------------------------------------
        # 4. ACTIVE APP VIEW CONTAINER
        # -------------------------------------------------------------
        self.app_view = QWidget(self)
        self.app_view.setGeometry(0, 0, 1024, 600)
        self.app_view.hide()
        
        self.app_opacity = QGraphicsOpacityEffect(self.app_view)
        self.app_view.setGraphicsEffect(self.app_opacity)
        
        self.app_view_layout = QVBoxLayout(self.app_view)
        self.app_view_layout.setContentsMargins(0, 0, 0, 0)
        self.app_view_layout.setSpacing(0)
        
        self.app_stack = QStackedWidget()
        self.app_view_layout.addWidget(self.app_stack)

        self.anim_app_group = QParallelAnimationGroup()
        self.anim_app_geom = QPropertyAnimation(self.app_view, b"geometry")
        self.anim_app_fade = QPropertyAnimation(self.app_opacity, b"opacity")
        self.anim_app_group.addAnimation(self.anim_app_geom)
        self.anim_app_group.addAnimation(self.anim_app_fade)

        self.edge_interceptor = QWidget(self)
        self.edge_interceptor.setGeometry(0, 0, 25, 600)
        self.edge_interceptor.setStyleSheet("background-color: transparent;")
        self.edge_interceptor.raise_() 

        # -------------------------------------------------------------
        # 5. DUAL BACKGROUND RECURRING ENGINE UPDATERS
        # -------------------------------------------------------------
        self.update_check_timer = QTimer(self)
        self.update_check_timer.timeout.connect(self.check_for_system_update)
        self.update_check_timer.start(86400000) 
        QTimer.singleShot(5000, self.check_for_system_update)

        self.app_update_timer = QTimer(self)
        self.app_update_timer.timeout.connect(self.check_for_app_updates)
        self.app_update_timer.start(86400000) 
        QTimer.singleShot(8000, self.check_for_app_updates)

    def show_toast(self, app_name, title, desc, icon):
        """Creates and fires a One UI system-wide pop-up notification."""
        if hasattr(self, 'current_toast') and self.current_toast:
            self.current_toast.deleteLater()
            
        self.current_toast = ToastNotification(self, app_name, title, desc, icon, self.launch_app)
        self.current_toast.show_toast()

    # =================================================================
    # BACKGROUND ENGINE TASKS (SYSTEM & APP STORE)
    # =================================================================
    def check_for_system_update(self):
        if hasattr(self, 'update_thread') and self.update_thread and self.update_thread.isRunning():
            return
        self.update_thread = SystemUpdateCheckThread()
        self.update_thread.update_detected.connect(self.on_system_update_detected)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.start()

    def on_system_update_detected(self, new_version):
        if getattr(self, '_notified_update_version', None) == new_version:
            return
        self._notified_update_version = new_version
        desc = "There is new update available."
        
        self.add_notification("Settings", desc, "⚙️")
        self.show_toast("Settings", "System Update", desc, "⚙️")

    def check_for_app_updates(self):
        """Spawns an isolated thread checking remote repository packages mapping local files only."""
        if hasattr(self, 'app_update_thread') and self.app_update_thread and self.app_update_thread.isRunning():
            return
        self.app_update_thread = AppStoreUpdateCheckThread()
        self.app_update_thread.updates_detected.connect(self.on_app_updates_detected)
        self.app_update_thread.finished.connect(self.app_update_thread.deleteLater)
        self.app_update_thread.start()

    def on_app_updates_detected(self, apps_list):
        count = len(apps_list)
        toast_desc = f"{count} app{'s' if count > 1 else ''} need updates."
        expanded_desc = f"Updates available for: {', '.join(apps_list)}."
        
        self.add_notification("App Store", expanded_desc, "📦")
        self.show_toast("App Store", "App Updates", toast_desc, "📦")

    # =================================================================
    # NOTIFICATION CENTER METHODS
    # =================================================================
    def add_notification(self, title, desc, icon="🔔"):
        card = QFrame()
        card.setStyleSheet("background-color: #22222B; border-radius: 12px; border: 1px solid #2F2F3B;")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 14, 14)
        layout.setSpacing(15)
        
        lbl_icon = QLabel(icon)
        lbl_icon.setFont(QFont("Google Sans", 24))
        lbl_icon.setFixedSize(45, 45)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("background-color: rgba(255,255,255,10); border-radius: 22px; border: none;")
        
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Google Sans", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setFont(QFont("Google Sans", 13))
        lbl_desc.setStyleSheet("color: #AAAAAA; border: none;")
        lbl_desc.setWordWrap(True)
        
        text_box.addWidget(lbl_title)
        text_box.addWidget(lbl_desc)
        
        btn_dismiss = QPushButton("✕")
        btn_dismiss.setFixedSize(36, 36)
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.setFont(QFont("Google Sans", 15, QFont.Weight.Bold))
        btn_dismiss.setStyleSheet("""
            QPushButton { background: transparent; color: #888888; border: none; border-radius: 18px; }
            QPushButton:hover { background: rgba(226,74,74,40); color: #E24A4A; }
        """)
        btn_dismiss.clicked.connect(lambda: self.remove_notification(card))
        
        layout.addWidget(lbl_icon)
        layout.addLayout(text_box, stretch=1)
        layout.addWidget(btn_dismiss)
        
        self.notif_layout.insertWidget(0, card)
        self.update_notif_header()

    def remove_notification(self, card_widget):
        card_widget.deleteLater()
        QTimer.singleShot(50, self.update_notif_header)

    def clear_all_notifications(self):
        for i in reversed(range(self.notif_layout.count())):
            item = self.notif_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()
        QTimer.singleShot(50, self.update_notif_header)

    def update_notif_header(self):
        count = 0
        for i in range(self.notif_layout.count()):
            w = self.notif_layout.itemAt(i).widget()
            if w and w != self.empty_label:
                count += 1

        if count == 0:
            self.lbl_notif_count.setText("No New Notifications")
            if not self.empty_label:
                self.empty_label = QLabel("You're all caught up! ✨")
                self.empty_label.setFont(QFont("Google Sans", 16))
                self.empty_label.setStyleSheet("color: #666670; margin-top: 40px;")
                self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.notif_layout.addWidget(self.empty_label)
        else:
            if self.empty_label:
                self.empty_label.deleteLater()
                self.empty_label = None
            self.lbl_notif_count.setText(f"Recent Alerts ({count})")

    def switch_cc_page(self, index):
        if index == self.cc_index: return
        target_x = -1024 if index > self.cc_index else 1024
        
        current_page = self.cc_pages[self.cc_index]
        next_page = self.cc_pages[index]
        next_page.show()
        next_page.move(target_x, 0)
        
        self.animate_carousel(current_page, QRect(-target_x, 0, 1024, 440), next_page, QRect(0, 0, 1024, 440), index)
        self.update_cc_tabs(index)

    def update_cc_tabs(self, active_idx):
        self.cc_index = active_idx
        if active_idx == 0:
            self.btn_tab_settings.setStyleSheet(self.cc_tab_active)
            self.btn_tab_notifs.setStyleSheet(self.cc_tab_inactive)
        else:
            self.btn_tab_settings.setStyleSheet(self.cc_tab_inactive)
            self.btn_tab_notifs.setStyleSheet(self.cc_tab_active)

    # =================================================================
    # TASK SWITCHER BUTTON & EXPANDING RIBBON
    # =================================================================
    def toggle_task_ribbon(self):
        if not self.running_apps:
            self.task_ribbon.hide()
            return
        self.task_ribbon.setVisible(not self.task_ribbon.isVisible())

    def update_task_switcher(self):
        count = len(self.running_apps)
        if count > 0:
            self.lbl_task_badge.setText(str(count))
            self.lbl_task_badge.show()
        else:
            self.lbl_task_badge.hide()
            self.task_ribbon.hide()
            return

        for i in reversed(range(self.ribbon_layout.count())):
            item = self.ribbon_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget(): sub.widget().deleteLater()

        for app_name in list(self.running_apps.keys()):
            card = QFrame()
            card.setFixedSize(200, 75)
            card.setStyleSheet("background-color: #24242E; border-radius: 12px; border: 1px solid #333340;")
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 10, 8)
            card_layout.setSpacing(10)
            
            btn_switch = QPushButton(app_name)
            btn_switch.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_switch.setFont(QFont("Google Sans", 13, QFont.Weight.Bold))
            btn_switch.setStyleSheet("""
                QPushButton { background: transparent; color: white; border: none; text-align: left; }
                QPushButton:hover { color: #3EA6FF; }
            """)
            btn_switch.clicked.connect(lambda checked, a=app_name: self.launch_app(a))
            
            btn_kill = QPushButton("✕")
            btn_kill.setFixedSize(32, 32)
            btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_kill.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
            btn_kill.setStyleSheet("""
                QPushButton { background-color: rgba(226, 74, 74, 30); color: #E24A4A; border-radius: 16px; border: none; }
                QPushButton:hover { background-color: #E24A4A; color: white; }
            """)
            btn_kill.clicked.connect(lambda checked, a=app_name: self.kill_app(a))
            
            card_layout.addWidget(btn_switch, stretch=1)
            card_layout.addWidget(btn_kill)
            self.ribbon_layout.addWidget(card)

        if count > 1:
            btn_close_all = QPushButton("Close All")
            btn_close_all.setFixedSize(100, 75)
            btn_close_all.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close_all.setFont(QFont("Google Sans", 12, QFont.Weight.Bold))
            btn_close_all.setStyleSheet("""
                QPushButton { background-color: rgba(226, 74, 74, 20); color: #E24A4A; border: 1px dashed #E24A4A; border-radius: 12px; }
                QPushButton:hover { background-color: #E24A4A; color: white; border-style: solid; }
            """)
            btn_close_all.clicked.connect(self.kill_all_apps)
            self.ribbon_layout.addWidget(btn_close_all)

        self.ribbon_layout.addStretch()

    def kill_app(self, app_name):
        if app_name in self.running_apps:
            widget = self.running_apps.pop(app_name)
            self.app_stack.removeWidget(widget)
            widget.deleteLater()
            self.update_task_switcher()

    def kill_all_apps(self):
        for app_name in list(self.running_apps.keys()):
            self.kill_app(app_name)

    # =================================================================
    # DYNAMIC APP CATALOG SCANNER & RESPONSIVE GRID
    # =================================================================
    def rebuild_app_drawer(self):
        scale = 100
        layout_type = "grid"
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    conf = json.load(f)
                    scale = conf.get("app_drawer_scale", 100)
                    layout_type = conf.get("app_drawer_layout", "grid")
        except Exception: 
            pass

        for i in reversed(range(self.drawer_grid.count())):
            item = self.drawer_grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater() 

        for i in range(self.drawer_grid.rowCount()):
            self.drawer_grid.setRowStretch(i, 0)

        core_apps = [
            ("App Store", "icons/appstore.png"),
            ("Character.ai", "icons/character_ai.svg"),
            ("Local Music", "icons/music.svg")
        ]

        downloaded_apps = []
        if os.path.exists("apps"):
            for filename in sorted(os.listdir("apps")):
                if filename.endswith(".py") and filename not in ["__init__.py", "app_store.py", "local_music.py", "web_app.py", "settings.py"]:
                    clean_name = filename.replace(".py", "").replace("_", " ").title()
                    png_name = filename.replace(".py", ".png")
                    svg_name = filename.replace(".py", ".svg")
                    
                    if os.path.exists(os.path.join("icons", png_name)):
                        icon_path = os.path.join("icons", png_name)
                    else:
                        icon_path = os.path.join("icons", svg_name)
                    downloaded_apps.append((clean_name, icon_path))

        system_apps = [
            ("Games", "icons/games.svg"),
            ("Clockfaces", "icons/clock.svg"),
            ("Settings", "icons/settings.svg")
        ]

        seen_names = set()
        all_apps = []
        for app_name, icon_path in core_apps + downloaded_apps + system_apps:
            if app_name not in seen_names:
                seen_names.add(app_name)
                all_apps.append((app_name, icon_path))

        if layout_type == "grid":
            self.drawer_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            self.drawer_grid.setSpacing(35) 
            columns = max(1, int(4 * (100.0 / scale)))
            if columns > 6: columns = 6
        else:
            self.drawer_grid.setAlignment(Qt.AlignmentFlag.AlignTop) 
            self.drawer_grid.setSpacing(10)
            columns = 1 

        for idx, (app_name, icon_path) in enumerate(all_apps):
            row = idx // columns
            col = idx % columns
            app_widget = DynamicAppButton(app_name, icon_path, self.launch_app, scale, layout_type)
            self.drawer_grid.addWidget(app_widget, row, col)

    # =================================================================
    # GESTURE ENGINE
    # =================================================================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            self.active_gesture = None

            if not self.app_view.isHidden() and self.drag_start_pos.x() <= 50:
                self.active_gesture = 'edge_swipe_back'

    def mouseMoveEvent(self, event):
        if not self.drag_start_pos:
            return

        current_pos = event.position().toPoint()
        dx = current_pos.x() - self.drag_start_pos.x()
        dy = current_pos.y() - self.drag_start_pos.y()

        if self.active_gesture is None and (abs(dx) > 15 or abs(dy) > 15):
            if abs(dy) > abs(dx):
                if self.app_drawer.is_visible:
                    if dy > 0: self.active_gesture = 'close_drawer'
                elif self.control_center.is_visible:
                    if dy < 0: self.active_gesture = 'close_controls'
                elif self.app_view.isHidden():
                    if dy < 0:
                        self.active_gesture = 'open_drawer'
                        self.app_drawer.raise_()
                    elif dy > 0:
                        self.active_gesture = 'open_controls'
                        self.control_center.raise_()
            else:
                if self.control_center.is_visible:
                    self.active_gesture = 'cc_horizontal'
                elif not self.app_drawer.is_visible and self.app_view.isHidden():
                    self.active_gesture = 'horizontal'

        if self.active_gesture == 'edge_swipe_back':
            new_x = max(0, min(1024, dx))
            self.app_view.move(new_x, 0)
        elif self.active_gesture == 'open_drawer':
            new_y = max(0, min(600, 600 + dy))
            self.app_drawer.move(0, new_y)
        elif self.active_gesture == 'close_drawer':
            new_y = max(0, min(600, dy))
            self.app_drawer.move(0, new_y)
        elif self.active_gesture == 'open_controls':
            new_y = max(-500, min(0, -500 + dy))
            self.control_center.move(0, new_y)
        elif self.active_gesture == 'close_controls':
            new_y = max(-500, min(0, dy))
            self.control_center.move(0, new_y)
        elif self.active_gesture == 'cc_horizontal':
            current_page = self.cc_pages[self.cc_index]
            other_index = 1 if self.cc_index == 0 else 0
            other_page = self.cc_pages[other_index]
            
            current_page.move(dx, 0)
            other_page.show()
            if dx < 0:
                other_page.move(1024 + dx, 0)
            else:
                other_page.move(-1024 + dx, 0)
        elif self.active_gesture == 'horizontal':
            current_page = self.home_pages[self.home_index]
            current_page.move(dx, 0)
            if dx < 0 and self.home_index < len(self.home_pages) - 1:
                next_page = self.home_pages[self.home_index + 1]
                next_page.show()
                next_page.move(1024 + dx, 0)
            elif dx > 0 and self.home_index > 0:
                prev_page = self.home_pages[self.home_index - 1]
                prev_page.show()
                prev_page.move(-1024 + dx, 0)

    def mouseReleaseEvent(self, event):
        if not self.drag_start_pos or not self.active_gesture:
            self.drag_start_pos = None
            return

        current_pos = event.position().toPoint()
        dx = current_pos.x() - self.drag_start_pos.x()
        dy = current_pos.y() - self.drag_start_pos.y()

        if self.active_gesture == 'edge_swipe_back':
            if dx > 150: self.animate_app_close()
            else:        self.animate_app_snap_back()
        elif self.active_gesture == 'open_drawer':
            if dy < -120: 
                self.rebuild_app_drawer()  
                self.app_drawer.slide_in()
            else:         
                self.app_drawer.slide_out()
        elif self.active_gesture == 'open_controls':
            if dy > 120:  self.control_center.slide_in()
            else:         self.control_center.slide_out()
        elif self.active_gesture == 'close_drawer':
            if dy > 120:  self.app_drawer.slide_out()
            else:         self.app_drawer.slide_in()
        elif self.active_gesture == 'close_controls':
            if dy < -120: self.control_center.slide_out()
            else:         self.control_center.slide_in()
        elif self.active_gesture == 'cc_horizontal':
            current_page = self.cc_pages[self.cc_index]
            other_index = 1 if self.cc_index == 0 else 0
            other_page = self.cc_pages[other_index]
            
            if abs(dx) > 150:
                target_x = -1024 if dx < 0 else 1024
                self.animate_carousel(current_page, QRect(target_x, 0, 1024, 440), other_page, QRect(0, 0, 1024, 440), other_index)
                self.update_cc_tabs(other_index)
            else:
                self.animate_carousel(current_page, QRect(0, 0, 1024, 440))
                other_page.move(1024 if dx < 0 else -1024, 0)
        elif self.active_gesture == 'horizontal':
            current_page = self.home_pages[self.home_index]
            if dx < -200 and self.home_index < len(self.home_pages) - 1:
                next_page = self.home_pages[self.home_index + 1]
                self.animate_carousel(current_page, QRect(-1024, 0, 1024, 600), next_page, QRect(0, 0, 1024, 600), self.home_index + 1)
            elif dx > 200 and self.home_index > 0:
                prev_page = self.home_pages[self.home_index - 1]
                self.animate_carousel(current_page, QRect(1024, 0, 1024, 600), prev_page, QRect(0, 0, 1024, 600), self.home_index - 1)
            else:
                self.animate_carousel(current_page, QRect(0, 0, 1024, 600))
                if self.home_index < len(self.home_pages) - 1:
                    self.home_pages[self.home_index + 1].move(1024, 0)
                if self.home_index > 0:
                    self.home_pages[self.home_index - 1].move(-1024, 0)

        self.drag_start_pos = None
        self.active_gesture = None

    def animate_carousel(self, page1, target1, page2=None, target2=None, new_index=None):
        self.anim_current = QPropertyAnimation(page1, b"geometry")
        self.anim_current.setDuration(250)
        self.anim_current.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_current.setEndValue(target1)
        self.anim_current.start()

        if page2 and target2:
            self.anim_next = QPropertyAnimation(page2, b"geometry")
            self.anim_next.setDuration(250)
            self.anim_next.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim_next.setEndValue(target2)
            self.anim_next.start()
            if new_index is not None:
                if page1 in self.home_pages:
                    self.home_index = new_index
                else:
                    self.cc_index = new_index

    # =================================================================
    # APP LAUNCHING & ROUTING
    # =================================================================
    def launch_app(self, app_name):
        self.app_drawer.slide_out()
        self.task_ribbon.hide()
        self.control_center.slide_out()
        
        if app_name in self.running_apps:
            self.app_stack.setCurrentWidget(self.running_apps[app_name])
        else:
            page_instance = None
            if app_name == "Character.ai":
                page_instance = create_web_app_view("https://character.ai", app_name, self.minimize_app)
            elif app_name == "Local Music":
                page_instance = LocalMusicPage()
            elif app_name == "App Store":
                page_instance = AppStorePage()
            else:
                loaded_successfully = False
                try:
                    module_name = app_name.lower().replace(" ", "_")
                    if os.path.exists(os.path.join("apps", f"{module_name}.py")):
                        mod = importlib.import_module(f"apps.{module_name}")
                        importlib.reload(mod) 
                        
                        for attr_name in dir(mod):
                            if attr_name.endswith("Page") and attr_name not in ["AppStorePage", "LocalMusicPage"]:
                                page_class = getattr(mod, attr_name)
                                try:
                                    page_instance = page_class(on_close=self.minimize_app)
                                except TypeError:
                                    page_instance = page_class()  
                                    
                                loaded_successfully = True
                                break
                except Exception as e:
                    print(f"Error launching dynamic app '{app_name}': {e}")

                if not loaded_successfully:
                    app_box = QWidget()
                    layout = QVBoxLayout(app_box)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    app_title = QLabel(f"{app_name} Module")
                    app_title.setFont(QFont("Google Sans", 32, QFont.Weight.Bold))
                    desc = QLabel("Swipe from the far left edge of the screen to return home.")
                    desc.setStyleSheet("color: #888888; font-size: 16px; margin-top: 10px;")
                    layout.addWidget(app_title, alignment=Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter)
                    
                    btn_close = QPushButton("Return Home")
                    btn_close.setFixedSize(200, 50)
                    btn_close.setStyleSheet("background-color: #E24A4A; border-radius: 10px; color: white;")
                    btn_close.clicked.connect(self.minimize_app)
                    layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
                    
                    page_instance = app_box

            self.app_stack.addWidget(page_instance)
            self.running_apps[app_name] = page_instance
            self.app_stack.setCurrentWidget(page_instance)
            self.update_task_switcher()

        start_rect = QRect(int(1024 * 0.075), int(600 * 0.075), int(1024 * 0.85), int(600 * 0.85))
        self.app_view.setGeometry(start_rect) 
        self.app_opacity.setOpacity(0.0)
        self.app_view.show()
        self.app_view.raise_()
        
        if hasattr(self, 'edge_interceptor'):
            self.edge_interceptor.raise_()

        self.anim_app_group.stop()
        self.anim_app_geom.setDuration(250) 
        self.anim_app_geom.setEasingCurve(QEasingCurve.Type.OutCubic) 
        self.anim_app_geom.setStartValue(start_rect)
        self.anim_app_geom.setEndValue(QRect(0, 0, 1024, 600))
        
        self.anim_app_fade.setDuration(250)
        self.anim_app_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_app_fade.setStartValue(0.0)
        self.anim_app_fade.setEndValue(1.0)
        
        self.anim_app_group.start()

    def animate_app_close(self):
        self.anim_app_group.stop()
        
        end_rect = QRect(int(1024 * 0.075), int(600 * 0.075), int(1024 * 0.85), int(600 * 0.85))
        
        self.anim_app_geom.setDuration(200)
        self.anim_app_geom.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_app_geom.setStartValue(self.app_view.geometry())
        self.anim_app_geom.setEndValue(end_rect)
        
        self.anim_app_fade.setDuration(200)
        self.anim_app_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_app_fade.setStartValue(self.app_opacity.opacity())
        self.anim_app_fade.setEndValue(0.0)
        
        self.anim_app_group.finished.connect(self.on_app_closed)
        self.anim_app_group.start()

    def animate_app_snap_back(self):
        self.anim_app_group.stop()
        self.anim_app_geom.setDuration(200)
        self.anim_app_geom.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_app_geom.setStartValue(self.app_view.geometry())
        self.anim_app_geom.setEndValue(QRect(0, 0, 1024, 600))
        
        self.anim_app_fade.setDuration(200)
        self.anim_app_fade.setStartValue(self.app_opacity.opacity())
        self.anim_app_fade.setEndValue(1.0)
        
        self.anim_app_group.start()

    def on_app_closed(self):
        try:
            self.anim_app_group.finished.disconnect(self.on_app_closed)
        except TypeError:
            pass
        self.app_view.hide()
        self.app_opacity.setOpacity(1.0) 
        self.app_view.move(0, 0)

    def minimize_app(self):
        self.animate_app_close()