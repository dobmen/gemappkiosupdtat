import os
import socket
import shutil
import json
import urllib.request
import time
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QSlider, QStackedWidget, QScroller, QSizePolicy, QProgressBar, QDialog
)

# =================================================================
# ⚙️ OS UPDATE CONFIGURATION
# =================================================================
UPDATE_URL = "https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/main/os_version.json"


class CheckUpdateThread(QThread):
    """Background thread to fetch the latest OS version from GitHub."""
    on_success = pyqtSignal(dict)
    on_error = pyqtSignal(str)

    def __init__(self, channel="main"):
        super().__init__()
        self.channel = channel

    def run(self):
        try:
            update_url = f"https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/{self.channel}/os_version.json"
            cache_busting_url = f"{update_url}?t={int(time.time())}"
            req = urllib.request.Request(cache_busting_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                self.on_success.emit(data)
        except Exception as e:
            self.on_error.emit(str(e))


class ModernDialog(QDialog):
    """A sleek, Android/One UI style popup dialog."""
    def __init__(self, parent, title, message, accept_text="OK", cancel_text="Cancel"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(520, 300)

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
        lbl_msg.setMinimumHeight(80) 

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
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; border: none; padding: 0 25px; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        btn_accept.clicked.connect(self.accept)
        btn_layout.addWidget(btn_accept)

        bg_layout.addLayout(btn_layout)
        layout.addWidget(bg_frame)


class CategoryButton(QPushButton):
    def __init__(self, title, icon_path):
        super().__init__(f"  {title}")
        self.setFixedHeight(75) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(28, 28))
            
        self.setStyleSheet(self.get_inactive_style())

    def get_inactive_style(self):
        return """
            QPushButton {
                background-color: transparent;
                color: #AAAAAA;
                border-radius: 12px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 10); }
        """

    def get_active_style(self):
        return """
            QPushButton {
                background-color: rgba(90, 141, 239, 40);
                color: #5A8DEF;
                border: 1px solid #5A8DEF;
                border-radius: 12px;
                text-align: left;
                padding-left: 20px;
            }
        """

    def set_active(self, is_active):
        if is_active:
            self.setStyleSheet(self.get_active_style())
        else:
            self.setStyleSheet(self.get_inactive_style())


class SettingsPage(QWidget):
    def __init__(self, on_close=None):
        super().__init__()
        self.on_close = on_close
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_area = QWidget()
        content_area.setStyleSheet("background-color: #0C0C0E;")
        h_layout = QHBoxLayout(content_area)
        h_layout.setContentsMargins(20, 20, 20, 20)
        h_layout.setSpacing(20)

        left_container = QFrame()
        left_container.setFixedWidth(280) 
        left_container.setStyleSheet("background-color: #1C1C22; border-radius: 16px; border: 1px solid #2C2C35;")
        left_container_layout = QVBoxLayout(left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(0)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(nav_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        nav_content = QWidget()
        nav_content.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(nav_content)
        left_layout.setContentsMargins(15, 20, 15, 20)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.category_buttons = []
        categories = [
            ("Network and Wi-Fi", "icons/network.png"),
            ("Display", "icons/display.png"),
            ("Audio and Sound", "icons/audio.png"),
            ("Customize", "icons/customize.png"),
            ("Installed Apps", "icons/apps.png"),
            ("System Storage", "icons/storage.png"),
            ("Software Update", "icons/update.png"),
            ("Power", "icons/power.png")
        ]

        for i, (title, icon_path) in enumerate(categories):
            btn = CategoryButton(title, icon_path)
            btn.clicked.connect(lambda checked, idx=i: self.switch_category(idx))
            self.category_buttons.append(btn)
            left_layout.addWidget(btn)

        nav_scroll.setWidget(nav_content)
        left_container_layout.addWidget(nav_scroll)

        h_layout.addWidget(left_container)

        self.right_stack = QStackedWidget()
        self.right_stack.setStyleSheet("background: transparent;")
        self.right_stack.setMinimumWidth(500) 
        
        self.right_stack.addWidget(self.create_network_page())
        self.right_stack.addWidget(self.create_display_page())
        self.right_stack.addWidget(self.create_audio_page())
        self.right_stack.addWidget(self.create_customize_page())
        self.right_stack.addWidget(self.create_apps_page())
        self.right_stack.addWidget(self.create_storage_page())
        self.right_stack.addWidget(self.create_update_page()) 
        self.right_stack.addWidget(self.create_power_page())

        h_layout.addWidget(self.right_stack, stretch=1) 
        main_layout.addWidget(content_area)

        self.switch_category(0)

    def switch_category(self, index):
        self.right_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.category_buttons):
            btn.set_active(i == index)
        if index == 3:
            self.update_clockface_preview()
        elif index == 4:
            self.refresh_apps_list()

    def get_saved_setting(self, key, default):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                    return config.get(key, default)
        except Exception:
            pass
        return default

    def save_setting(self, key, value):
        config = {}
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
        except Exception:
            pass
            
        config[key] = value
        
        try:
            with open("config.json", "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save setting: {e}")

    # =================================================================
    # CATEGORY PAGES
    # =================================================================
    def create_network_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Network Status")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        ip_address = self.get_local_ip()
        lbl_status = QLabel("Status: Connected")
        lbl_status.setFont(QFont("Google Sans", 18))
        lbl_status.setStyleSheet("color: #1ED760; border: none;")
        
        lbl_ip = QLabel(f"IP Address: {ip_address}")
        lbl_ip.setFont(QFont("Google Sans", 16))
        lbl_ip.setStyleSheet("color: #CCCCCC; border: none;")
        
        card_layout.addWidget(lbl_status)
        card_layout.addWidget(lbl_ip)
        layout.addWidget(card)

        btn_wifi = QPushButton("Scan Networks")
        btn_wifi.setFixedSize(200, 60) 
        btn_wifi.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        btn_wifi.setStyleSheet("QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }")
        layout.addSpacing(20)
        layout.addWidget(btn_wifi)
        
        layout.addStretch()
        return page

    def create_display_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Display")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        bright_header = QHBoxLayout()
        lbl_bright = QLabel("Screen Brightness")
        lbl_bright.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_bright.setStyleSheet("color: white; border: none;")
        
        saved_brightness = self.get_saved_setting("brightness", 80)
        self.lbl_bright_val = QLabel(f"{saved_brightness}%")
        self.lbl_bright_val.setFont(QFont("Google Sans", 16))
        self.lbl_bright_val.setStyleSheet("color: #5A8DEF; border: none;")
        
        bright_header.addWidget(lbl_bright)
        bright_header.addStretch()
        bright_header.addWidget(self.lbl_bright_val)
        card_layout.addLayout(bright_header)
        
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(10, 100)
        self.bright_slider.setValue(saved_brightness)
        
        self.bright_slider.setStyleSheet("""
            QSlider { background: transparent; height: 50px; }
            QSlider::groove:horizontal { height: 8px; background: rgba(255, 255, 255, 30); border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #5A8DEF; border-radius: 4px; }
            QSlider::handle:horizontal { width: 24px; margin: -8px 0; background: white; border-radius: 12px; }
        """)
        self.bright_slider.valueChanged.connect(self.update_brightness_val)
        card_layout.addWidget(self.bright_slider)
        
        layout.addWidget(card)
        layout.addStretch()
        return page

    def update_brightness_val(self, val):
        self.lbl_bright_val.setText(f"{val}%")
        self.save_setting("brightness", val)

    def create_audio_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Audio and Sound")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        
        vol_header = QHBoxLayout()
        lbl_vol = QLabel("System Sounds Volume")
        lbl_vol.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_vol.setStyleSheet("color: white; border: none;")
        
        saved_vol = self.get_saved_setting("system_volume", 80)
        self.lbl_vol_val = QLabel(f"{saved_vol}%")
        self.lbl_vol_val.setFont(QFont("Google Sans", 16))
        self.lbl_vol_val.setStyleSheet("color: #5A8DEF; border: none;")
        
        vol_header.addWidget(lbl_vol)
        vol_header.addStretch()
        vol_header.addWidget(self.lbl_vol_val)
        card_layout.addLayout(vol_header)
        
        self.sys_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.sys_vol_slider.setRange(0, 100)
        self.sys_vol_slider.setValue(saved_vol)
        self.sys_vol_slider.setStyleSheet("""
            QSlider { background: transparent; height: 50px; }
            QSlider::groove:horizontal { height: 8px; background: rgba(255, 255, 255, 30); border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #5A8DEF; border-radius: 4px; }
            QSlider::handle:horizontal { width: 24px; margin: -8px 0; background: white; border-radius: 12px; }
        """)
        self.sys_vol_slider.valueChanged.connect(self.update_volume_val)
        card_layout.addWidget(self.sys_vol_slider)

        card_layout.addSpacing(10)

        self.is_silent = self.get_saved_setting("silent_mode", False)
        self.btn_silent = QPushButton()
        self.update_toggle_btn(self.btn_silent, "Silent Mode", self.is_silent, "silent")
        self.btn_silent.clicked.connect(self.toggle_silent)
        card_layout.addWidget(self.btn_silent)

        self.is_dnd = self.get_saved_setting("dnd_mode", False)
        self.btn_dnd = QPushButton()
        self.update_toggle_btn(self.btn_dnd, "Do Not Disturb", self.is_dnd, "dnd")
        self.btn_dnd.clicked.connect(self.toggle_dnd)
        card_layout.addWidget(self.btn_dnd)

        container_layout.addWidget(card)
        container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def update_volume_val(self, val):
        self.lbl_vol_val.setText(f"{val}%")
        self.save_setting("system_volume", val)

    def update_toggle_btn(self, btn, text, state, mode_type="default"):
        btn.setFixedHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        
        icon_file = ""
        if mode_type == "silent":
            active_bg = "#E24A4A"  # Red
            icon_file = "icons/silent.png"
        elif mode_type == "dnd":
            active_bg = "#7B61FF"  # Blue-purple
            icon_file = "icons/dnd.png"
        else:
            active_bg = "#5A8DEF"

        if os.path.exists(icon_file):
            btn.setIcon(QIcon(icon_file))
            btn.setIconSize(QSize(24, 24))
            btn.setText(f"  {text} (ON)" if state else f"  {text} (OFF)")
        else:
            btn.setIcon(QIcon())
            btn.setText(f"{text} (ON)" if state else f"{text} (OFF)")

        if state:
            btn.setStyleSheet(f"QPushButton {{ background-color: {active_bg}; color: white; border-radius: 12px; text-align: left; padding-left: 20px; border: none; }}")
        else:
            btn.setStyleSheet("QPushButton { background-color: #2C2C35; color: #AAAAAA; border-radius: 12px; text-align: left; padding-left: 20px; border: none; }")

    def toggle_silent(self):
        self.is_silent = not self.is_silent
        self.save_setting("silent_mode", self.is_silent)
        self.update_toggle_btn(self.btn_silent, "Silent Mode", self.is_silent, "silent")

    def toggle_dnd(self):
        self.is_dnd = not self.is_dnd
        self.save_setting("dnd_mode", self.is_dnd)
        self.update_toggle_btn(self.btn_dnd, "Do Not Disturb", self.is_dnd, "dnd")

    def create_customize_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Customize Interface")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(container)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        c_layout = QVBoxLayout(card)
        
        scale_header = QHBoxLayout()
        lbl_scale = QLabel("App Drawer Icon Scale")
        lbl_scale.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_scale.setStyleSheet("color: white; border: none;")
        
        saved_scale = self.get_saved_setting("app_drawer_scale", 100)
        self.lbl_scale_val = QLabel(f"{saved_scale}%")
        self.lbl_scale_val.setFont(QFont("Google Sans", 16))
        self.lbl_scale_val.setStyleSheet("color: #5A8DEF; border: none;")
        
        scale_header.addWidget(lbl_scale)
        scale_header.addStretch()
        scale_header.addWidget(self.lbl_scale_val)
        c_layout.addLayout(scale_header)
        
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 200) 
        self.scale_slider.setValue(saved_scale)
        self.scale_slider.setStyleSheet("""
            QSlider { background: transparent; height: 50px; }
            QSlider::groove:horizontal { height: 8px; background: rgba(255, 255, 255, 30); border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #5A8DEF; border-radius: 4px; }
            QSlider::handle:horizontal { width: 24px; margin: -8px 0; background: white; border-radius: 12px; }
        """)
        self.scale_slider.valueChanged.connect(self.update_scale_val)
        c_layout.addWidget(self.scale_slider)
        
        c_layout.addSpacing(15)

        lbl_layout = QLabel("App Drawer Layout")
        lbl_layout.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_layout.setStyleSheet("color: white; border: none;")
        c_layout.addWidget(lbl_layout)

        layout_btns = QHBoxLayout()
        layout_btns.setSpacing(15)
        
        self.btn_grid = QPushButton("⊞ Grid View")
        self.btn_grid.setFixedHeight(60) 
        self.btn_grid.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_grid.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        self.btn_grid.clicked.connect(lambda: self.set_app_layout("grid"))
        
        self.btn_list = QPushButton("☰ List View")
        self.btn_list.setFixedHeight(60)
        self.btn_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_list.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        self.btn_list.clicked.connect(lambda: self.set_app_layout("list"))

        layout_btns.addWidget(self.btn_grid)
        layout_btns.addWidget(self.btn_list)
        c_layout.addLayout(layout_btns)
        
        card_layout.addWidget(card)
        card_layout.addSpacing(20)

        lbl_cf = QLabel("Watch Face")
        lbl_cf.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_cf.setStyleSheet("color: white; border: none;")
        card_layout.addWidget(lbl_cf)

        cf_card = QFrame()
        cf_card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        cf_layout = QHBoxLayout(cf_card)
        cf_layout.setContentsMargins(15, 15, 15, 15)
        cf_layout.setSpacing(15)
        
        self.lbl_cf_preview = QLabel()
        self.lbl_cf_preview.setFixedSize(90, 90)
        self.lbl_cf_preview.setStyleSheet("background: transparent;")
        self.lbl_cf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cf_layout.addWidget(self.lbl_cf_preview)
        
        cf_info = QVBoxLayout()
        cf_name = QLabel("Current Clockface")
        cf_name.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        cf_name.setStyleSheet("color: white; border: none; background: transparent;")
        
        btn_change_cf = QPushButton("Change Clockface")
        btn_change_cf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_cf.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 14px; border: none; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        btn_change_cf.clicked.connect(self.open_clockface_selector)
        
        cf_info.addWidget(cf_name)
        cf_info.addWidget(btn_change_cf)
        cf_info.addStretch()
        
        cf_layout.addLayout(cf_info)
        cf_layout.addStretch()
        card_layout.addWidget(cf_card)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        saved_layout = self.get_saved_setting("app_drawer_layout", "grid")
        self.set_app_layout(saved_layout, save=False)
        self.update_clockface_preview()
        
        return page

    def update_clockface_preview(self):
        try:
            from components.clockfaces import CLOCKFACES
            from PyQt6.QtCore import QTime, QDate
            
            idx = self.get_saved_setting("clockface_index", 0)
            if idx < len(CLOCKFACES):
                inst = CLOCKFACES[idx][1]()
                inst.setGeometry(0, 0, 360, 360)
                inst.update_time(QTime.currentTime(), QDate.currentDate())
                
                pix = QPixmap(360, 360)
                pix.fill(Qt.GlobalColor.transparent)
                inst.render(pix)
                
                circular_pix = QPixmap(90, 90)
                circular_pix.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(circular_pix)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                
                painter.setPen(QPen(QColor("#5A8DEF"), 2))
                painter.setBrush(QColor("#0C0C0E"))
                painter.drawEllipse(1, 1, 88, 88)
                
                path = QPainterPath()
                path.addEllipse(2, 2, 86, 86)
                painter.setClipPath(path)
                
                scaled = pix.scaled(86, 86, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (86 - scaled.width()) // 2 + 2
                y = (86 - scaled.height()) // 2 + 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                
                self.lbl_cf_preview.setPixmap(circular_pix)
        except Exception as e:
            print(f"Could not load clockface preview: {e}")

    def open_clockface_selector(self):
        main_window = self.window()
        if hasattr(main_window, 'open_clockface_selector'):
            if self.on_close:
                self.on_close()
            main_window.open_clockface_selector()

    # =================================================================
    # INSTALLED APPS PAGE W/ ICONS & UNINSTALLER
    # =================================================================
    def create_apps_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Installed Applications")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.apps_container = QWidget()
        self.apps_container.setStyleSheet("background: transparent;")
        self.apps_layout = QVBoxLayout(self.apps_container)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(14)
        self.apps_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.apps_container)
        layout.addWidget(scroll)

        self.refresh_apps_list()
        return page

    def refresh_apps_list(self):
        while self.apps_layout.count():
            item = self.apps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Added gallery.py firmly to core_apps
        core_apps = ["settings.py", "app_store.py", "__init__.py", "kiosk.py", "local_music.py", "spotify.py", "web_app.py", "gallery.py"]
        
        try:
            if not os.path.exists("apps"):
                os.makedirs("apps", exist_ok=True)
            
            files = [f for f in os.listdir("apps") if f.endswith(".py") and not f.startswith("__")]
            
            # Sort system apps to top, handling case sensitivity correctly
            files.sort(key=lambda x: (x.lower() not in core_apps, x.lower()))
        except Exception as e:
            lbl_err = QLabel(f"Error loading apps: {e}")
            lbl_err.setStyleSheet("color: #E24A4A; font-size: 16px;")
            self.apps_layout.addWidget(lbl_err)
            return

        if not files:
            lbl_empty = QLabel("No applications installed.")
            lbl_empty.setFont(QFont("Google Sans", 16))
            lbl_empty.setStyleSheet("color: #AAAAAA; margin-top: 40px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.apps_layout.addWidget(lbl_empty)
            return

        for filename in files:
            card = QFrame()
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 16px 20px;")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(15)

            app_id = filename[:-3].lower() 
            app_name = "Music" if app_id == "local_music" else app_id.replace("_", " ").title()

            lbl_icon = QLabel()
            lbl_icon.setFixedSize(48, 48)
            lbl_icon.setStyleSheet("background: transparent; border: none;")
            
            icon_path = ""
            if os.path.exists(os.path.join("icons", f"{app_id}.png")):
                icon_path = os.path.join("icons", f"{app_id}.png")
            elif os.path.exists(os.path.join("icons", f"{app_id}.svg")):
                icon_path = os.path.join("icons", f"{app_id}.svg")
                
            target_pix = QPixmap(48, 48)
            target_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(target_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            original_pix = QIcon(icon_path).pixmap(QSize(48, 48)) if icon_path else QPixmap()
            
            if not original_pix.isNull():
                path = QPainterPath()
                path.addRoundedRect(0, 0, 48, 48, 12, 12)
                painter.setClipPath(path)
                scaled = original_pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (48 - scaled.width()) // 2
                y = (48 - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                colors = ["#E24A4A", "#5A8DEF", "#F39C12", "#27AE60", "#8E44AD", "#9B59B6"]
                painter.setBrush(QColor(colors[len(app_name) % len(colors)]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(0, 0, 48, 48)
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("Google Sans", 20, QFont.Weight.Bold))
                painter.drawText(QRect(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, app_name[0].upper())
            painter.end()
            lbl_icon.setPixmap(target_pix)

            ver_file = os.path.join("apps", f"{app_id}.ver")
            version_str = ""
            if os.path.exists(ver_file):
                try:
                    with open(ver_file, "r") as f:
                        version_str = f"v{f.read().strip()}"
                except Exception:
                    pass
            
            # Locked Case-Insensitive Core Match Check
            is_core = filename.lower() in core_apps

            info_box = QVBoxLayout()
            info_box.setSpacing(4)
            
            lbl_name = QLabel(app_name)
            lbl_name.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: white; border: none; background: transparent;")
            
            status_text = "System OS Application" if is_core else f"App Store Download • {version_str if version_str else 'Installed'}"
            lbl_status = QLabel(status_text)
            lbl_status.setFont(QFont("Google Sans", 13))
            lbl_status.setStyleSheet(f"color: {'#5A8DEF' if is_core else '#888888'}; border: none; background: transparent;")
            
            info_box.addWidget(lbl_name)
            info_box.addWidget(lbl_status)
            
            card_layout.addWidget(lbl_icon)
            card_layout.addLayout(info_box)
            card_layout.addStretch()

            if is_core:
                btn_lock = QPushButton("🔒 System App")
                btn_lock.setFixedSize(140, 42)
                btn_lock.setEnabled(False)
                btn_lock.setStyleSheet("""
                    QPushButton { background-color: #2C2C35; color: #666670; border-radius: 8px; font-weight: bold; font-size: 14px; border: none; }
                """)
                card_layout.addWidget(btn_lock)
            else:
                btn_uninstall = QPushButton("🗑️ Uninstall")
                btn_uninstall.setFixedSize(130, 42)
                btn_uninstall.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_uninstall.setStyleSheet("""
                    QPushButton { background-color: rgba(226, 74, 74, 20); color: #E24A4A; border: 1px solid #E24A4A; border-radius: 8px; font-weight: bold; font-size: 14px; }
                    QPushButton:hover { background-color: #E24A4A; color: white; }
                """)
                btn_uninstall.clicked.connect(lambda checked, fname=filename, name=app_name: self.uninstall_app(fname, name))
                card_layout.addWidget(btn_uninstall)

            self.apps_layout.addWidget(card)

    def uninstall_app(self, filename, app_name):
        dialog = ModernDialog(
            self,
            "Uninstall Application",
            f"Are you sure you want to completely uninstall {app_name} from Kiosk OS?",
            "Uninstall"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                app_id = filename[:-3]
                script_path = os.path.join("apps", filename)
                ver_path = os.path.join("apps", f"{app_id}.ver")
                
                if os.path.exists(script_path):
                    os.remove(script_path)
                if os.path.exists(ver_path):
                    os.remove(ver_path)
                    
                if os.path.exists("icons"):
                    for icon_file in os.listdir("icons"):
                        if os.path.splitext(icon_file)[0] == app_id:
                            try: os.remove(os.path.join("icons", icon_file))
                            except Exception: pass
                                
                self.refresh_apps_list()
            except Exception as e:
                err_dialog = ModernDialog(self, "Uninstall Failed", f"Could not remove {app_name}: {str(e)}", "OK", "")
                err_dialog.exec()

    def create_storage_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("System Storage")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        storage_info = self.get_storage_info()
        lbl_sys = QLabel(storage_info)
        lbl_sys.setFont(QFont("Google Sans", 18))
        lbl_sys.setStyleSheet("color: #CCCCCC; border: none;")
        card_layout.addWidget(lbl_sys)
        
        layout.addWidget(card)
        layout.addStretch()
        return page

    # =================================================================
    # UPDATE PAGE W/ BETA TOGGLE
    # =================================================================
    def create_update_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Software Update")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        self.current_os_version = self.get_saved_setting("os_version", "0.1.0")
        
        self.lbl_update_status = QLabel(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Your system is up to date.")
        self.lbl_update_status.setFont(QFont("Google Sans", 16))
        self.lbl_update_status.setStyleSheet("color: #CCCCCC; border: none;")
        card_layout.addWidget(self.lbl_update_status)
        
        self.update_progress = QProgressBar()
        self.update_progress.setFixedHeight(6)
        self.update_progress.setTextVisible(False)
        self.update_progress.setRange(0, 0)
        self.update_progress.setStyleSheet("""
            QProgressBar { background: transparent; border: none; border-radius: 3px; } 
            QProgressBar::chunk { background: #5A8DEF; border-radius: 3px; }
        """)
        self.update_progress.hide()
        
        card_layout.addSpacing(10)
        card_layout.addWidget(self.update_progress)
        card_layout.addSpacing(15)

        # BETA TOGGLE SWITCH
        self.is_beta = self.get_saved_setting("update_channel", "main") == "beta"
        self.btn_beta = QPushButton()
        self.update_toggle_btn(self.btn_beta, "Receive Beta Updates", self.is_beta)
        self.btn_beta.clicked.connect(self.toggle_beta)
        card_layout.addWidget(self.btn_beta)
        
        layout.addWidget(card)

        self.btn_check_update = QPushButton("Check for Updates")
        self.btn_check_update.setFixedSize(250, 60) 
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        self.btn_check_update.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }
            QPushButton:disabled { background-color: #2C2C35; color: #555555; }
        """)
        self.btn_check_update.clicked.connect(self.trigger_update_check)
        
        layout.addSpacing(20)
        layout.addWidget(self.btn_check_update)
        
        layout.addStretch()
        return page

    def toggle_beta(self):
        self.is_beta = not self.is_beta
        channel = "beta" if self.is_beta else "main"
        self.save_setting("update_channel", channel)
        self.update_toggle_btn(self.btn_beta, "Receive Beta Updates", self.is_beta)
        
        self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Switched to {channel.upper()} channel.")
        self.btn_check_update.setText("Check for Updates")
        self.btn_check_update.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }
            QPushButton:disabled { background-color: #2C2C35; color: #555555; }
        """)
        try:
            self.btn_check_update.clicked.disconnect()
        except Exception:
            pass
        self.btn_check_update.clicked.connect(self.trigger_update_check)

    def trigger_update_check(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Checking GitHub...")
        
        channel = "beta" if self.is_beta else "main"
        self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Connecting to {channel} update server...")
        self.update_progress.show()
        
        self.checker = CheckUpdateThread(channel)
        self.checker.on_success.connect(self.on_update_checked)
        self.checker.on_error.connect(self.on_update_error)
        self.checker.start()

    def on_update_checked(self, data):
        self.update_progress.hide()
        self.btn_check_update.setEnabled(True)
        
        latest_version = data.get("version", "0.0.0")
        release_notes = data.get("notes", "No notes provided.")
        
        if latest_version > self.current_os_version:
            self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nNew Version Available: v{latest_version}\nNotes: {release_notes}")
            self.btn_check_update.setText("⬇ Download & Install")
            self.btn_check_update.setStyleSheet("""
                QPushButton { background-color: #1ED760; color: #0C0C0E; border-radius: 12px; }
            """)
            
            self.btn_check_update.clicked.disconnect()
            self.btn_check_update.clicked.connect(lambda: self.install_update(latest_version))
        else:
            self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Your system is up to date.")
            self.btn_check_update.setText("Check Again")

    def on_update_error(self, err_msg):
        self.update_progress.hide()
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Retry Check")
        self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Update failed.\nError: {err_msg}")

    def install_update(self, new_version):
        channel = "beta" if self.is_beta else "main"
        dialog = ModernDialog(
            self, 
            "Confirm Update", 
            f"Installing version {new_version} from the {channel} channel will automatically reboot the Kiosk system.\n\nDo you want to proceed?",
            "Install & Reboot"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.btn_check_update.setEnabled(False)
            self.btn_check_update.setText("Installing...")
            self.update_progress.show()
            self.lbl_update_status.setText(f"Status: Pulling latest code from GitHub...\nPlease do not turn off the device.")
            
            self.save_setting("os_version", new_version)
            git_cmd = f"git fetch origin && git switch -C {channel} origin/{channel} && sudo reboot"
            QTimer.singleShot(1500, lambda: os.system(git_cmd))

    def create_power_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Power Options")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        btn_reboot = QPushButton("🔄 Reboot Kiosk")
        btn_reboot.setFixedHeight(75) 
        btn_reboot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reboot.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        btn_reboot.setStyleSheet("""
            QPushButton { background-color: #2C2C35; color: white; border-radius: 12px; }
        """)
        btn_reboot.clicked.connect(self.reboot_system)
        layout.addWidget(btn_reboot)
        
        layout.addSpacing(10)

        btn_shutdown = QPushButton("⏻ Shutdown")
        btn_shutdown.setFixedHeight(75) 
        btn_shutdown.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_shutdown.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        btn_shutdown.setStyleSheet("""
            QPushButton { background-color: #E24A4A; color: white; border-radius: 12px; }
        """)
        btn_shutdown.clicked.connect(self.shutdown_system)
        layout.addWidget(btn_shutdown)

        layout.addStretch()
        return page

    # =================================================================
    # SYSTEM CONFIG HELPERS
    # =================================================================
    def update_scale_val(self, val):
        self.lbl_scale_val.setText(f"{val}%")
        self.save_setting("app_drawer_scale", val)

    def set_app_layout(self, layout_type, save=True):
        active_style = """
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; border: none; }
        """
        inactive_style = """
            QPushButton { background-color: #2C2C35; color: #AAAAAA; border-radius: 8px; border: none; }
        """
        
        if layout_type == "grid":
            self.btn_grid.setStyleSheet(active_style)
            self.btn_list.setStyleSheet(inactive_style)
        else:
            self.btn_grid.setStyleSheet(inactive_style)
            self.btn_list.setStyleSheet(active_style)
            
        if save:
            self.save_setting("app_drawer_layout", layout_type)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def get_storage_info(self):
        try:
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (2**30)
            total_gb = total // (2**30)
            return f"Free Space: {free_gb} GB\nTotal Size: {total_gb} GB"
        except Exception:
            return "Storage information unavailable."

    def reboot_system(self):
        dialog = ModernDialog(self, "Reboot System", "Are you sure you want to reboot the kiosk?", "Reboot")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            os.system("sudo reboot")

    def shutdown_system(self):
        dialog = ModernDialog(self, "Shutdown System", "Are you sure you want to completely shut down?", "Shutdown")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            os.system("sudo shutdown now")