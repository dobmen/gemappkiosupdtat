import os
import socket
import shutil
import json
import urllib.request
import time
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QSlider, QMessageBox, QStackedWidget, QScroller, QSizePolicy, QProgressBar
)

# =================================================================
# ⚙️ OS UPDATE CONFIGURATION
# =================================================================
UPDATE_URL = "https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/main/os_version.json"


class CheckUpdateThread(QThread):
    """Background thread to fetch the latest OS version from GitHub."""
    on_success = pyqtSignal(dict)
    on_error = pyqtSignal(str)

    def run(self):
        try:
            cache_busting_url = f"{UPDATE_URL}?t={int(time.time())}"
            req = urllib.request.Request(cache_busting_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                self.on_success.emit(data)
        except Exception as e:
            self.on_error.emit(str(e))


class CategoryButton(QPushButton):
    def __init__(self, title, icon):
        super().__init__(f"{icon}  {title}")
        self.setFixedHeight(75) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
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
            ("Network & Wi-Fi", "📶"),
            ("Display", "☀️"),
            ("Audio & Sound", "🔊"),
            ("Customize", "🎨"),
            ("System Storage", "💾"),
            ("Software Update", "🔄"),
            ("Power", "⚡")
        ]

        for i, (title, icon) in enumerate(categories):
            btn = CategoryButton(title, icon)
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
        btn_wifi.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }
        """)
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
        
        lbl_bright = QLabel("Screen Brightness")
        lbl_bright.setFont(QFont("Google Sans", 16))
        lbl_bright.setStyleSheet("color: #CCCCCC; border: none;")
        card_layout.addWidget(lbl_bright)
        
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(10, 100)
        
        saved_brightness = self.get_saved_setting("brightness", 80)
        self.bright_slider.setValue(saved_brightness)
        
        self.bright_slider.setStyleSheet("""
            QSlider { background: transparent; height: 50px; }
            QSlider::groove:horizontal { height: 8px; background: rgba(255, 255, 255, 30); border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #5A8DEF; border-radius: 4px; }
            QSlider::handle:horizontal { width: 24px; margin: -8px 0; background: white; border-radius: 12px; }
        """)
        self.bright_slider.valueChanged.connect(lambda v: self.save_setting("brightness", v))
        card_layout.addWidget(self.bright_slider)
        
        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_audio_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Audio & Sound")
        title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(20)

        # Make content scrollable for small displays
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
        
        # 1. System Sounds Volume Slider
        lbl_vol = QLabel("System Sounds Volume")
        lbl_vol.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_vol.setStyleSheet("color: white; border: none;")
        card_layout.addWidget(lbl_vol)
        
        self.sys_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.sys_vol_slider.setRange(0, 100)
        self.sys_vol_slider.setValue(self.get_saved_setting("system_volume", 80))
        self.sys_vol_slider.setStyleSheet("""
            QSlider { background: transparent; height: 50px; }
            QSlider::groove:horizontal { height: 8px; background: rgba(255, 255, 255, 30); border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #5A8DEF; border-radius: 4px; }
            QSlider::handle:horizontal { width: 24px; margin: -8px 0; background: white; border-radius: 12px; }
        """)
        self.sys_vol_slider.valueChanged.connect(lambda v: self.save_setting("system_volume", v))
        card_layout.addWidget(self.sys_vol_slider)

        card_layout.addSpacing(10)

        # 2. Silent Mode Toggle
        self.is_silent = self.get_saved_setting("silent_mode", False)
        self.btn_silent = QPushButton()
        self.update_toggle_btn(self.btn_silent, "Silent Mode (Mute System Sounds)", self.is_silent)
        self.btn_silent.clicked.connect(self.toggle_silent)
        card_layout.addWidget(self.btn_silent)

        # 3. Do Not Disturb Toggle
        self.is_dnd = self.get_saved_setting("dnd_mode", False)
        self.btn_dnd = QPushButton()
        self.update_toggle_btn(self.btn_dnd, "Do Not Disturb (Hide Pop-up Notifications)", self.is_dnd)
        self.btn_dnd.clicked.connect(self.toggle_dnd)
        card_layout.addWidget(self.btn_dnd)

        container_layout.addWidget(card)
        container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def update_toggle_btn(self, btn, text, state):
        """Helper to style toggle buttons beautifully."""
        btn.setFixedHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
        if state:
            btn.setText(f"✓  {text}")
            btn.setStyleSheet("QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; text-align: left; padding-left: 20px; border: none; }")
        else:
            btn.setText(f"✕  {text}")
            btn.setStyleSheet("QPushButton { background-color: #2C2C35; color: #AAAAAA; border-radius: 12px; text-align: left; padding-left: 20px; border: none; }")

    def toggle_silent(self):
        self.is_silent = not self.is_silent
        self.save_setting("silent_mode", self.is_silent)
        self.update_toggle_btn(self.btn_silent, "Silent Mode (Mute System Sounds)", self.is_silent)

    def toggle_dnd(self):
        self.is_dnd = not self.is_dnd
        self.save_setting("dnd_mode", self.is_dnd)
        self.update_toggle_btn(self.btn_dnd, "Do Not Disturb (Hide Pop-up Notifications)", self.is_dnd)

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

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        saved_scale = self.get_saved_setting("app_drawer_scale", 100)
        
        scale_header = QHBoxLayout()
        lbl_scale = QLabel("App Drawer Icon Scale")
        lbl_scale.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_scale.setStyleSheet("color: white; border: none;")
        
        self.lbl_scale_val = QLabel(f"{saved_scale}%")
        self.lbl_scale_val.setFont(QFont("Google Sans", 16))
        self.lbl_scale_val.setStyleSheet("color: #5A8DEF; border: none;")
        
        scale_header.addWidget(lbl_scale)
        scale_header.addStretch()
        scale_header.addWidget(self.lbl_scale_val)
        card_layout.addLayout(scale_header)
        
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
        card_layout.addWidget(self.scale_slider)
        
        card_layout.addSpacing(15)

        lbl_layout = QLabel("App Drawer Layout")
        lbl_layout.setFont(QFont("Google Sans", 16, QFont.Weight.Bold))
        lbl_layout.setStyleSheet("color: white; border: none;")
        card_layout.addWidget(lbl_layout)

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
        card_layout.addLayout(layout_btns)

        layout.addWidget(card)
        layout.addStretch()
        
        saved_layout = self.get_saved_setting("app_drawer_layout", "grid")
        self.set_app_layout(saved_layout, save=False)
        return page

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

    def trigger_update_check(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Checking GitHub...")
        
        self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Connecting to update server...")
        self.update_progress.show()
        
        self.checker = CheckUpdateThread()
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
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Installing...")
        self.update_progress.show()
        self.lbl_update_status.setText(f"Status: Pulling latest code from GitHub...\nPlease do not turn off the device.")
        
        self.save_setting("os_version", new_version)
        QTimer.singleShot(1500, lambda: os.system("git fetch origin && git reset --hard origin/main && sudo reboot"))


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
        reply = QMessageBox.question(
            self, 'Reboot System', 'Are you sure you want to reboot the kiosk?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.system("sudo reboot")

    def shutdown_system(self):
        reply = QMessageBox.question(
            self, 'Shutdown System', 'Are you sure you want to completely shut down?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.system("sudo shutdown now")