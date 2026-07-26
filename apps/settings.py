import os
import socket
import shutil
import json
import urllib.request
import time
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QSlider, QStackedWidget, QScroller, QSizePolicy, QProgressBar, QDialog, QLineEdit, QScrollerProperties,
    QListWidget, QListWidgetItem
)

def get_scale_factor():
    screen = QGuiApplication.primaryScreen()
    return max(1.0, screen.size().width() / 1024.0) if screen else 1.0


class CheckUpdateThread(QThread):
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
                
                size_mb = "Unknown"
                if "main_script_url" in data:
                    try:
                        size_req = urllib.request.Request(data["main_script_url"], method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(size_req, timeout=5) as size_resp:
                            bytes_size = int(size_resp.headers.get('Content-Length', 0))
                            if bytes_size > 0:
                                size_mb = f"{(bytes_size / (1024 * 1024)):.2f} MB"
                    except Exception:
                        pass
                
                data['calculated_size'] = size_mb
                self.on_success.emit(data)
        except Exception as e:
            self.on_error.emit(str(e))


class ModernDialog(QDialog):
    def __init__(self, parent, title, message, accept_text="OK", cancel_text="Cancel"):
        super().__init__(parent)
        scale = get_scale_factor()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(int(520 * scale), int(300 * scale))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bg_frame = QFrame(self)
        bg_frame.setStyleSheet("background-color: #22222B; border-radius: 20px; border: 1px solid #33333F;")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(int(30 * scale), int(30 * scale), int(30 * scale), int(25 * scale))
        bg_layout.setSpacing(int(15 * scale))

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Google Sans", int(20 * scale), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")

        lbl_msg = QLabel(message)
        lbl_msg.setFont(QFont("Google Sans", int(15 * scale)))
        lbl_msg.setStyleSheet("color: #CCCCCC; border: none;")
        lbl_msg.setWordWrap(True)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        bg_layout.addWidget(lbl_title)
        bg_layout.addWidget(lbl_msg)
        bg_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(int(15 * scale))
        btn_layout.addStretch()

        if cancel_text:
            btn_cancel = QPushButton(cancel_text)
            btn_cancel.setFixedHeight(int(45 * scale))
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet("""
                QPushButton { background: transparent; color: white; border-radius: 8px; font-weight: bold; padding: 0 20px; }
                QPushButton:hover { background-color: rgba(255,255,255,10); }
            """)
            btn_cancel.setFont(QFont("Google Sans", int(15 * scale), QFont.Weight.Bold))
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)

        btn_accept = QPushButton(accept_text)
        btn_accept.setFixedHeight(int(45 * scale))
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; border: none; padding: 0 25px; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        btn_accept.setFont(QFont("Google Sans", int(15 * scale), QFont.Weight.Bold))
        btn_accept.clicked.connect(self.accept)
        btn_layout.addWidget(btn_accept)

        bg_layout.addLayout(btn_layout)
        layout.addWidget(bg_frame)


class DeleteClockfaceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        scale = get_scale_factor()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(int(520 * scale), int(380 * scale))
        self.deleted_any = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        bg_frame = QFrame(self)
        bg_frame.setStyleSheet("background-color: #22222B; border-radius: 24px; border: 1px solid #33333F;")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(int(25 * scale), int(25 * scale), int(25 * scale), int(20 * scale))

        lbl_title = QLabel("Delete Downloaded Clockfaces")
        lbl_title.setFont(QFont("Google Sans", int(18 * scale), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none;")
        bg_layout.addWidget(lbl_title)
        bg_layout.addSpacing(int(10 * scale))

        self.list_widget = QListWidget()
        QScroller.grabGesture(self.list_widget.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #14141A; border-radius: 12px; border: 1px solid #2C2C35; padding: 5px; color: white; outline: 0; }
            QListWidget::item { padding: 10px; border-radius: 8px; }
            QListWidget::item:selected { background-color: rgba(226, 74, 74, 40); color: #E24A4A; }
        """)
        self.list_widget.setFont(QFont("Google Sans", int(15 * scale)))
        
        self.files_map = {}
        if os.path.exists("clockfaces"):
            for f in sorted(os.listdir("clockfaces")):
                if f.endswith(".py") and not f.startswith("__"):
                    clean_name = f.replace(".py", "").replace("_", " ").title()
                    self.list_widget.addItem(clean_name)
                    self.files_map[clean_name] = f
                    
        if not self.files_map:
            self.list_widget.addItem("No custom clockfaces downloaded.")
            self.list_widget.setEnabled(False)
            
        bg_layout.addWidget(self.list_widget)
        bg_layout.addSpacing(int(15 * scale))
        
        actions = QHBoxLayout()
        actions.addStretch()
        
        btn_cancel = QPushButton("Close")
        btn_cancel.setFont(QFont("Google Sans", int(15 * scale), QFont.Weight.Bold))
        btn_cancel.setStyleSheet("QPushButton { background: transparent; color: #888888; border: none; }")
        btn_cancel.clicked.connect(self.accept)
        actions.addWidget(btn_cancel)

        self.btn_del = QPushButton("Delete Selected")
        self.btn_del.setFont(QFont("Google Sans", int(15 * scale), QFont.Weight.Bold))
        self.btn_del.setStyleSheet("QPushButton { background-color: #E24A4A; color: white; border-radius: 8px; padding: 8px 20px; border: none; }")
        self.btn_del.clicked.connect(self.confirm_delete)
        if not self.files_map:
            self.btn_del.hide()
        actions.addWidget(self.btn_del)
        
        bg_layout.addLayout(actions)
        layout.addWidget(bg_frame)

    def confirm_delete(self):
        selected = self.list_widget.selectedItems()
        if not selected: return
        
        name = selected[0].text()
        filename = self.files_map.get(name)
        if filename:
            try:
                os.remove(os.path.join("clockfaces", filename))
                ver_file = filename.replace(".py", ".ver")
                if os.path.exists(os.path.join("clockfaces", ver_file)):
                    os.remove(os.path.join("clockfaces", ver_file))
                    
                self.deleted_any = True
                self.list_widget.takeItem(self.list_widget.row(selected[0]))
                del self.files_map[name]
                
                if not self.files_map:
                    self.list_widget.clear()
                    self.list_widget.addItem("No custom clockfaces downloaded.")
                    self.list_widget.setEnabled(False)
                    self.btn_del.hide()

                main_win = self.window()
                if hasattr(main_win, 'selector_overlay'):
                    main_win.selector_overlay.reload_custom_clockfaces()
                    main_win.apply_clockface(0)
                    
                if hasattr(self.parent(), 'update_clockface_preview'):
                    self.parent().update_clockface_preview()
            except Exception as e:
                print("Error deleting", e)


class CategoryButton(QPushButton):
    def __init__(self, title, icon_path):
        super().__init__(f"  {title}")
        scale = get_scale_factor()
        self.setFixedHeight(int(75 * scale)) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Google Sans", int(16 * scale), QFont.Weight.Bold))
        
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(int(28 * scale), int(28 * scale)))
            
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
        self.scale = get_scale_factor()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_area = QWidget()
        content_area.setStyleSheet("background-color: #0C0C0E;")
        h_layout = QHBoxLayout(content_area)
        h_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        h_layout.setSpacing(int(20 * self.scale))

        left_container = QFrame()
        left_container.setFixedWidth(int(280 * self.scale)) 
        left_container.setStyleSheet("background-color: #1C1C22; border-radius: 16px; border: 1px solid #2C2C35;")
        left_container_layout = QVBoxLayout(left_container)
        left_container_layout.setContentsMargins(0, 0, 0, 0)
        left_container_layout.setSpacing(0)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        nav_scroller = QScroller.scroller(nav_scroll.viewport())
        nav_props = nav_scroller.scrollerProperties()
        nav_props.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy, QScrollerProperties.OvershootPolicy.OvershootAlwaysOff)
        nav_scroller.setScrollerProperties(nav_props)
        
        QScroller.grabGesture(nav_scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        nav_content = QWidget()
        nav_content.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(nav_content)
        left_layout.setContentsMargins(int(15 * self.scale), int(20 * self.scale), int(15 * self.scale), int(20 * self.scale))
        left_layout.setSpacing(int(10 * self.scale))
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.category_buttons = []
        categories = [
            ("Network and Wi-Fi", "icons/network.png"),
            ("Bluetooth", "icons/bluetooth.png"),
            ("Display", "icons/display.png"),
            ("Audio and Sound", "icons/audio.png"),
            ("Customize", "icons/customize.png"),
            ("Installed Apps", "icons/apps.png"),
            ("Voice Assistant", "icons/assistant.svg"),
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
        
        self.right_stack.addWidget(self.create_network_page())
        self.right_stack.addWidget(self.create_bluetooth_page())
        self.right_stack.addWidget(self.create_display_page())
        self.right_stack.addWidget(self.create_audio_page())
        self.right_stack.addWidget(self.create_customize_page())
        self.right_stack.addWidget(self.create_apps_page())
        self.right_stack.addWidget(self.create_assistant_page())
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

    def create_network_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Network Status")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        self.card_layout = QVBoxLayout(card)
        self.card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        self.lbl_status = QLabel("Status: Checking...")
        self.lbl_status.setFont(QFont("Google Sans", int(18 * self.scale)))
        self.lbl_status.setStyleSheet("color: #CCCCCC; border: none;")
        
        self.lbl_ip = QLabel("IP Address: Checking...")
        self.lbl_ip.setFont(QFont("Google Sans", int(16 * self.scale)))
        self.lbl_ip.setStyleSheet("color: #CCCCCC; border: none;")
        
        self.card_layout.addWidget(self.lbl_status)
        self.card_layout.addWidget(self.lbl_ip)
        layout.addWidget(card)

        btn_wifi = QPushButton("Scan Networks")
        btn_wifi.setFixedSize(int(200 * self.scale), int(60 * self.scale)) 
        btn_wifi.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        btn_wifi.setStyleSheet("QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }")
        btn_wifi.clicked.connect(self.scan_networks)
        layout.addSpacing(int(20 * self.scale))
        layout.addWidget(btn_wifi)
        
        self.networks_container = QWidget()
        self.networks_layout = QVBoxLayout(self.networks_container)
        self.networks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(self.networks_container)
        layout.addWidget(scroll)
        
        self.scan_networks()
        return page

    def scan_networks(self):
        # Clear existing
        while self.networks_layout.count():
            item = self.networks_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        import subprocess
        try:
            # Check current Wi-Fi connection
            res = subprocess.check_output(["nmcli", "-t", "-f", "active,ssid,bssid,signal", "dev", "wifi"], stderr=subprocess.STDOUT).decode('utf-8')
            lines = res.strip().split('\n')
            
            connected_ssid = None
            networks = []
            for line in lines:
                parts = line.split(':')
                if len(parts) >= 4:
                    active = parts[0]
                    ssid = parts[1]
                    if active == 'yes':
                        connected_ssid = ssid
                    if ssid and ssid not in [n['ssid'] for n in networks]:
                        networks.append({'ssid': ssid, 'signal': parts[3]})
            
            ip_address = self.get_local_ip()
            if connected_ssid:
                self.lbl_status.setText(f"Status: Connected to Wi-Fi ({connected_ssid})")
                self.lbl_status.setStyleSheet("color: #1ED760; border: none;")
            else:
                # If no wifi, check if ethernet is connected (has IP and not loopback)
                if ip_address != "Not Connected" and ip_address != "127.0.0.1":
                    self.lbl_status.setText("Status: Connected to Ethernet")
                    self.lbl_status.setStyleSheet("color: #1ED760; border: none;")
                    networks = [] # Hide wifi list
                else:
                    self.lbl_status.setText("Status: Disconnected")
                    self.lbl_status.setStyleSheet("color: #E24A4A; border: none;")
                    
            self.lbl_ip.setText(f"IP Address: {ip_address}")
            
            if ip_address != "Not Connected" and ip_address != "127.0.0.1" and not connected_ssid:
                lbl = QLabel("Ethernet connection is active. Wi-Fi scanning is disabled.")
                lbl.setStyleSheet("color: #5A8DEF;")
                lbl.setFont(QFont("Google Sans", int(16 * self.scale)))
                self.networks_layout.addWidget(lbl)
            elif not networks:
                lbl = QLabel("No Wi-Fi networks found.")
                lbl.setStyleSheet("color: #AAAAAA;")
                lbl.setFont(QFont("Google Sans", int(16 * self.scale)))
                self.networks_layout.addWidget(lbl)
            else:
                for net in networks:
                    card = QFrame()
                    card.setStyleSheet("background-color: #24242E; border-radius: 8px; border: 1px solid #333340;")
                    layout = QHBoxLayout(card)
                    
                    lbl_ssid = QLabel(net['ssid'])
                    lbl_ssid.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
                    lbl_ssid.setStyleSheet("color: white; border: none;")
                    
                    lbl_sig = QLabel(f"Signal: {net['signal']}%")
                    lbl_sig.setFont(QFont("Google Sans", int(14 * self.scale)))
                    lbl_sig.setStyleSheet("color: #AAAAAA; border: none;")
                    
                    layout.addWidget(lbl_ssid)
                    layout.addStretch()
                    layout.addWidget(lbl_sig)
                    
                    if net['ssid'] != connected_ssid:
                        btn = QPushButton("Connect")
                        btn.setFixedSize(int(100 * self.scale), int(35 * self.scale))
                        btn.setStyleSheet("QPushButton { background-color: #333340; color: white; border-radius: 6px; } QPushButton:hover { background-color: #5A8DEF; }")
                        # (Connection logic would require password prompt, skipping for mock demo)
                        layout.addWidget(btn)
                    else:
                        lbl_conn = QLabel("Connected")
                        lbl_conn.setStyleSheet("color: #1ED760; border: none;")
                        lbl_conn.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
                        layout.addWidget(lbl_conn)
                        
                    self.networks_layout.addWidget(card)
        except Exception:
            # Fallback if nmcli not available (e.g. Mac/Windows testing or no NetworkManager)
            ip_address = self.get_local_ip()
            if ip_address != "Not Connected" and ip_address != "127.0.0.1":
                self.lbl_status.setText("Status: Connected (Ethernet/Unknown)")
                self.lbl_status.setStyleSheet("color: #1ED760; border: none;")
            else:
                self.lbl_status.setText("Status: Disconnected")
                self.lbl_status.setStyleSheet("color: #E24A4A; border: none;")
            self.lbl_ip.setText(f"IP Address: {ip_address}")
            
            lbl = QLabel("Network Manager (nmcli) not available. Cannot scan Wi-Fi.")
            lbl.setStyleSheet("color: #AAAAAA;")
            lbl.setFont(QFont("Google Sans", int(14 * self.scale)))
            self.networks_layout.addWidget(lbl)

    def create_bluetooth_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Bluetooth")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        self.btn_bt_toggle = QPushButton("Bluetooth: ON" if self.get_saved_setting("bluetooth_enabled", False) else "Bluetooth: OFF")
        self.btn_bt_toggle.setFixedSize(int(250 * self.scale), int(60 * self.scale)) 
        self.btn_bt_toggle.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        self.update_toggle_btn(self.btn_bt_toggle, "Bluetooth: ON", self.get_saved_setting("bluetooth_enabled", False))
        
        self.btn_bt_toggle.clicked.connect(lambda: self.toggle_bluetooth())
        layout.addWidget(self.btn_bt_toggle)
        layout.addSpacing(int(20 * self.scale))

        self.bt_container = QWidget()
        self.bt_layout = QVBoxLayout(self.bt_container)
        self.bt_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(self.bt_container)
        layout.addWidget(scroll)
        
        self.refresh_bluetooth_devices()
        return page

    def toggle_bluetooth(self):
        active = not self.get_saved_setting("bluetooth_enabled", False)
        self.save_setting("bluetooth_enabled", active)
        self.update_toggle_btn(self.btn_bt_toggle, "Bluetooth: ON" if active else "Bluetooth: OFF", active)
        self.refresh_bluetooth_devices()

    def refresh_bluetooth_devices(self):
        while self.bt_layout.count():
            item = self.bt_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not self.get_saved_setting("bluetooth_enabled", False):
            lbl = QLabel("Bluetooth is turned off.")
            lbl.setStyleSheet("color: #AAAAAA;")
            lbl.setFont(QFont("Google Sans", int(16 * self.scale)))
            self.bt_layout.addWidget(lbl)
            return
            
        devices = [
            ("AirPods Pro", "Connected"),
            ("Keychron K2", "Paired"),
            ("Logitech MX Master 3", "Available")
        ]
        
        for name, status in devices:
            card = QFrame()
            card.setStyleSheet("background-color: #2A2A35; border-radius: 8px;")
            c_layout = QHBoxLayout(card)
            
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: white; font-weight: bold;")
            lbl_name.setFont(QFont("Google Sans", int(16 * self.scale)))
            
            lbl_status = QLabel(status)
            lbl_status.setStyleSheet("color: #1ED760;" if status == "Connected" else "color: #AAAAAA;")
            lbl_status.setFont(QFont("Google Sans", int(14 * self.scale)))
            
            btn_connect = QPushButton("Disconnect" if status == "Connected" else "Connect")
            btn_connect.setStyleSheet("QPushButton { background-color: #333340; color: white; border-radius: 6px; padding: 5px 15px; } QPushButton:hover { background-color: #5A8DEF; }")
            
            c_layout.addWidget(lbl_name)
            c_layout.addWidget(lbl_status)
            c_layout.addStretch()
            c_layout.addWidget(btn_connect)
            
            self.bt_layout.addWidget(card)

    def create_display_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Display")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        bright_header = QHBoxLayout()
        lbl_bright = QLabel("Screen Brightness")
        lbl_bright.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        lbl_bright.setStyleSheet("color: white; border: none;")
        
        saved_brightness = self.get_saved_setting("brightness", 80)
        self.lbl_bright_val = QLabel(f"{saved_brightness}%")
        self.lbl_bright_val.setFont(QFont("Google Sans", int(16 * self.scale)))
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
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Audio and Sound")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy, QScrollerProperties.OvershootPolicy.OvershootAlwaysOff)
        scroller.setScrollerProperties(props)
        
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        card_layout.setSpacing(int(15 * self.scale))
        
        vol_header = QHBoxLayout()
        lbl_vol = QLabel("System Sounds Volume")
        lbl_vol.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        lbl_vol.setStyleSheet("color: white; border: none;")
        
        saved_vol = self.get_saved_setting("system_volume", 80)
        self.lbl_vol_val = QLabel(f"{saved_vol}%")
        self.lbl_vol_val.setFont(QFont("Google Sans", int(16 * self.scale)))
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

        card_layout.addSpacing(int(10 * self.scale))

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
        btn.setFixedHeight(int(60 * self.scale))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
        
        icon_file = ""
        if mode_type == "silent":
            active_bg = "#E24A4A"  
            icon_file = "icons/silent.png"
        elif mode_type == "dnd":
            active_bg = "#7B61FF"  
            icon_file = "icons/dnd.png"
        else:
            active_bg = "#5A8DEF"

        if os.path.exists(icon_file):
            btn.setIcon(QIcon(icon_file))
            btn.setIconSize(QSize(int(24 * self.scale), int(24 * self.scale)))
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
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Customize Interface")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy, QScrollerProperties.OvershootPolicy.OvershootAlwaysOff)
        scroller.setScrollerProperties(props)
        
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(container)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        scale_header = QHBoxLayout()
        lbl_scale = QLabel("App Drawer Icon Scale")
        lbl_scale.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        lbl_scale.setStyleSheet("color: white; border: none;")
        
        saved_scale = self.get_saved_setting("app_drawer_scale", 100)
        self.lbl_scale_val = QLabel(f"{saved_scale}%")
        self.lbl_scale_val.setFont(QFont("Google Sans", int(16 * self.scale)))
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
        self.scale_slider.sliderReleased.connect(self.apply_scale_val)
        c_layout.addWidget(self.scale_slider)
        
        c_layout.addSpacing(int(15 * self.scale))

        lbl_layout = QLabel("App Drawer Layout")
        lbl_layout.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        lbl_layout.setStyleSheet("color: white; border: none;")
        c_layout.addWidget(lbl_layout)

        layout_btns = QHBoxLayout()
        layout_btns.setSpacing(int(15 * self.scale))
        
        self.btn_grid = QPushButton("⊞ Grid View")
        self.btn_grid.setFixedHeight(int(60 * self.scale)) 
        self.btn_grid.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_grid.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
        self.btn_grid.clicked.connect(lambda: self.set_app_layout("grid"))
        
        self.btn_list = QPushButton("☰ List View")
        self.btn_list.setFixedHeight(int(60 * self.scale))
        self.btn_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_list.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
        self.btn_list.clicked.connect(lambda: self.set_app_layout("list"))

        layout_btns.addWidget(self.btn_grid)
        layout_btns.addWidget(self.btn_list)
        c_layout.addLayout(layout_btns)
        
        card_layout.addWidget(card)
        card_layout.addSpacing(int(20 * self.scale))

        lbl_cf = QLabel("Watch Face")
        lbl_cf.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        lbl_cf.setStyleSheet("color: white; border: none;")
        card_layout.addWidget(lbl_cf)

        cf_card = QFrame()
        cf_card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        cf_layout = QHBoxLayout(cf_card)
        cf_layout.setContentsMargins(int(15 * self.scale), int(15 * self.scale), int(15 * self.scale), int(15 * self.scale))
        cf_layout.setSpacing(int(15 * self.scale))
        
        preview_size = int(90 * self.scale)
        self.lbl_cf_preview = QLabel()
        self.lbl_cf_preview.setFixedSize(preview_size, preview_size)
        self.lbl_cf_preview.setStyleSheet("background: transparent;")
        self.lbl_cf_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cf_layout.addWidget(self.lbl_cf_preview)
        
        cf_info = QVBoxLayout()
        cf_info.setSpacing(int(10 * self.scale))
        cf_name = QLabel("Clockface Settings")
        cf_name.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
        cf_name.setStyleSheet("color: white; border: none; background: transparent;")
        
        btn_change_cf = QPushButton("Change Clockface")
        btn_change_cf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_cf.setFont(QFont("Google Sans", int(13 * self.scale), QFont.Weight.Bold))
        btn_change_cf.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; padding: 8px 14px; border: none; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        btn_change_cf.clicked.connect(self.open_clockface_selector)

        btn_delete_cf = QPushButton("🗑️ Delete")
        btn_delete_cf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete_cf.setFont(QFont("Google Sans", int(13 * self.scale), QFont.Weight.Bold))
        btn_delete_cf.setStyleSheet("""
            QPushButton { background-color: rgba(226, 74, 74, 20); color: #E24A4A; border-radius: 8px; padding: 8px 14px; border: 1px solid rgba(226, 74, 74, 100); }
            QPushButton:hover { background-color: #E24A4A; color: white; }
        """)
        btn_delete_cf.clicked.connect(self.open_delete_clockface_dialog)
        
        btns_layout = QHBoxLayout()
        btns_layout.addWidget(btn_change_cf)
        btns_layout.addWidget(btn_delete_cf)
        btns_layout.addStretch()

        cf_info.addWidget(cf_name)
        cf_info.addLayout(btns_layout)
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
                inst.setProperty("is_preview", True)
                inst.setGeometry(0, 0, 360, 360)
                inst.update_time(QTime.currentTime(), QDate.currentDate())
                
                pix = QPixmap(360, 360)
                pix.fill(Qt.GlobalColor.transparent)
                inst.render(pix)
                
                preview_size = int(90 * self.scale)
                circular_pix = QPixmap(preview_size, preview_size)
                circular_pix.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(circular_pix)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                
                painter.setPen(QPen(QColor("#5A8DEF"), 2))
                painter.setBrush(QColor("#0C0C0E"))
                painter.drawEllipse(1, 1, preview_size - 2, preview_size - 2)
                
                path = QPainterPath()
                path.addEllipse(2, 2, preview_size - 4, preview_size - 4)
                painter.setClipPath(path)
                
                scaled = pix.scaled(preview_size - 4, preview_size - 4, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (preview_size - 4 - scaled.width()) // 2 + 2
                y = (preview_size - 4 - scaled.height()) // 2 + 2
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

    def open_delete_clockface_dialog(self):
        dialog = DeleteClockfaceDialog(self)
        dialog.exec()
        if dialog.deleted_any:
            self.save_setting("clockface_index", 0)
            main_win = self.window()
            if hasattr(main_win, 'selector_overlay'):
                main_win.selector_overlay.reload_custom_clockfaces()
                main_win.apply_clockface(0)
            self.update_clockface_preview()

    def create_apps_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Installed Applications")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy, QScrollerProperties.OvershootPolicy.OvershootAlwaysOff)
        scroller.setScrollerProperties(props)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.apps_container = QWidget()
        self.apps_container.setStyleSheet("background: transparent;")
        self.apps_layout = QVBoxLayout(self.apps_container)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(int(14 * self.scale))
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

        core_apps = ["settings.py", "app_store.py", "__init__.py", "kiosk.py", "local_music.py", "spotify.py", "web_app.py", "gallery.py"]
        
        try:
            if not os.path.exists("apps"):
                os.makedirs("apps", exist_ok=True)
            
            files = [f for f in os.listdir("apps") if f.endswith(".py") and not f.startswith("__")]
            
            files.sort(key=lambda x: (x.lower() not in core_apps, x.lower()))
        except Exception as e:
            lbl_err = QLabel(f"Error loading apps: {e}")
            lbl_err.setStyleSheet("color: #E24A4A; font-size: 16px;")
            self.apps_layout.addWidget(lbl_err)
            return

        if not files:
            lbl_empty = QLabel("No applications installed.")
            lbl_empty.setFont(QFont("Google Sans", int(16 * self.scale)))
            lbl_empty.setStyleSheet("color: #AAAAAA; margin-top: 40px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.apps_layout.addWidget(lbl_empty)
            return

        for filename in files:
            card = QFrame()
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(int(20 * self.scale), int(16 * self.scale), int(20 * self.scale), int(16 * self.scale))
            card_layout.setSpacing(int(15 * self.scale))

            app_id = filename[:-3].lower() 
            app_name = "Music" if app_id == "local_music" else app_id.replace("_", " ").title()

            icon_size = int(48 * self.scale)
            lbl_icon = QLabel()
            lbl_icon.setFixedSize(icon_size, icon_size)
            lbl_icon.setStyleSheet("background: transparent; border: none;")
            
            icon_path = ""
            png_name = filename.replace(".py", ".png")
            svg_name = filename.replace(".py", ".svg")
            
            if os.path.exists(os.path.join("icons", png_name)):
                icon_path = os.path.join("icons", png_name)
            elif os.path.exists(os.path.join("icons", svg_name)):
                icon_path = os.path.join("icons", svg_name)
            elif os.path.exists(os.path.join("icons", f"{app_id}.png")):
                icon_path = os.path.join("icons", f"{app_id}.png")
            elif os.path.exists(os.path.join("icons", f"{app_id}.svg")):
                icon_path = os.path.join("icons", f"{app_id}.svg")
                
            target_pix = QPixmap(icon_size, icon_size)
            target_pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(target_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            original_pix = QIcon(icon_path).pixmap(QSize(icon_size, icon_size)) if icon_path else QPixmap()
            
            if not original_pix.isNull():
                path = QPainterPath()
                path.addRoundedRect(0, 0, icon_size, icon_size, 12, 12)
                painter.setClipPath(path)
                scaled = original_pix.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                x = (icon_size - scaled.width()) // 2
                y = (icon_size - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                colors = ["#E24A4A", "#5A8DEF", "#F39C12", "#27AE60", "#8E44AD", "#9B59B6"]
                painter.setBrush(QColor(colors[len(app_name) % len(colors)]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(0, 0, icon_size, icon_size)
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("Google Sans", int(20 * self.scale), QFont.Weight.Bold))
                painter.drawText(QRect(0, 0, icon_size, icon_size), Qt.AlignmentFlag.AlignCenter, app_name[0].upper())
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
            
            is_core = filename.lower() in core_apps

            info_box = QVBoxLayout()
            info_box.setSpacing(4)
            
            lbl_name = QLabel(app_name)
            lbl_name.setFont(QFont("Google Sans", int(18 * self.scale), QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: white; border: none; background: transparent;")
            
            status_text = "System OS Application" if is_core else f"App Store Download • {version_str if version_str else 'Installed'}"
            lbl_status = QLabel(status_text)
            lbl_status.setFont(QFont("Google Sans", int(13 * self.scale)))
            lbl_status.setStyleSheet(f"color: {'#5A8DEF' if is_core else '#888888'}; border: none; background: transparent;")
            
            info_box.addWidget(lbl_name)
            info_box.addWidget(lbl_status)
            
            card_layout.addWidget(lbl_icon)
            card_layout.addLayout(info_box)
            card_layout.addStretch()

            if is_core:
                btn_lock = QPushButton("🔒 System App")
                btn_lock.setFixedSize(int(140 * self.scale), int(42 * self.scale))
                btn_lock.setEnabled(False)
                btn_lock.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
                btn_lock.setStyleSheet("""
                    QPushButton { background-color: #2C2C35; color: #666670; border-radius: 8px; border: none; }
                """)
                card_layout.addWidget(btn_lock)
            else:
                btn_uninstall = QPushButton("🗑️ Uninstall")
                btn_uninstall.setFixedSize(int(130 * self.scale), int(42 * self.scale))
                btn_uninstall.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_uninstall.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
                btn_uninstall.setStyleSheet("""
                    QPushButton { background-color: rgba(226, 74, 74, 20); color: #E24A4A; border: 1px solid #E24A4A; border-radius: 8px; }
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

    def create_assistant_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Voice Assistant")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))
        
        info = QLabel("Voice Assistant is coming soon in a future update.\\nIt will allow you to control your smart home, play music, and ask questions hands-free.")
        info.setFont(QFont("Google Sans", int(20 * self.scale)))
        info.setStyleSheet("color: #AAAAAA;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addSpacing(int(20 * self.scale))

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        header = QHBoxLayout()
        lbl_enable = QLabel("Enable Voice Assistant")
        lbl_enable.setFont(QFont("Google Sans", int(22 * self.scale), QFont.Weight.Bold))
        lbl_enable.setStyleSheet("color: white; border: none;")
        
        toggle = QPushButton("Coming Soon")
        toggle.setFixedSize(int(160 * self.scale), int(50 * self.scale))
        toggle.setStyleSheet(f"QPushButton {{ background-color: #333340; color: #888890; border-radius: {int(25*self.scale)}px; font-weight: bold; font-size: {int(16*self.scale)}px; border: none; }}")
        toggle.setEnabled(False)
        
        header.addWidget(lbl_enable)
        header.addStretch()
        header.addWidget(toggle)
        
        card_layout.addLayout(header)
        
        desc = QLabel("Say 'Hey Ghost' or your custom wake word to trigger the assistant.")
        desc.setFont(QFont("Google Sans", int(14 * self.scale)))
        desc.setStyleSheet("color: #888888; border: none;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)
        
        layout.addWidget(card)
        layout.addStretch()
        
        return page

    def create_storage_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("System Storage")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        storage_info = self.get_storage_info()
        lbl_sys = QLabel(storage_info)
        lbl_sys.setFont(QFont("Google Sans", int(18 * self.scale)))
        lbl_sys.setStyleSheet("color: #CCCCCC; border: none;")
        card_layout.addWidget(lbl_sys)
        
        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_update_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Software Update")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("background-color: #1C1C22; border-radius: 12px; border: 1px solid #2C2C35;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(int(20 * self.scale), int(20 * self.scale), int(20 * self.scale), int(20 * self.scale))
        
        self.current_os_version = self.get_saved_setting("os_version", "0.1.0")
        
        self.lbl_update_status = QLabel(f"Kiosk OS Version: v{self.current_os_version}\n\nStatus: Your system is up to date.")
        self.lbl_update_status.setFont(QFont("Google Sans", int(16 * self.scale)))
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
        
        card_layout.addSpacing(int(10 * self.scale))
        card_layout.addWidget(self.update_progress)
        card_layout.addSpacing(int(15 * self.scale))

        self.is_beta = self.get_saved_setting("update_channel", "main") == "beta"
        self.btn_beta = QPushButton()
        self.update_toggle_btn(self.btn_beta, "Receive Beta Updates", self.is_beta)
        self.btn_beta.clicked.connect(self.toggle_beta)
        card_layout.addWidget(self.btn_beta)
        
        layout.addWidget(card)

        self.btn_check_update = QPushButton("Check for Updates")
        self.btn_check_update.setFixedSize(int(250 * self.scale), int(60 * self.scale)) 
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        self.btn_check_update.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }
            QPushButton:disabled { background-color: #2C2C35; color: #555555; }
        """)
        self.btn_check_update.clicked.connect(self.trigger_update_check)
        
        layout.addSpacing(int(20 * self.scale))
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
        payload_size = data.get("calculated_size", "Unknown")
        
        if latest_version > self.current_os_version:
            self.lbl_update_status.setText(f"Kiosk OS Version: v{self.current_os_version}\n\nNew Version Available: v{latest_version}  ({payload_size})\nNotes: {release_notes}")
            self.btn_check_update.setText("⬇ Download && Install")
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
            "Install && Reboot"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.btn_check_update.setEnabled(False)
            self.btn_check_update.setText("Installing...")
            self.update_progress.show()
            self.lbl_update_status.setText(f"Status: Pulling latest code from GitHub...\nPlease do not turn off the device.")
            
            self.save_setting("os_version", new_version)
            self.save_setting("just_updated", True)
            
            git_cmd = f"git fetch origin && git reset --hard origin/{channel} && systemctl reboot"
            QTimer.singleShot(1500, lambda: os.system(git_cmd))

    def create_power_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(int(30 * self.scale), int(20 * self.scale), int(30 * self.scale), int(30 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Power Options")
        title.setFont(QFont("Google Sans", int(24 * self.scale), QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addSpacing(int(20 * self.scale))

        btn_reboot = QPushButton("🔄 Reboot Kiosk")
        btn_reboot.setFixedHeight(int(75 * self.scale)) 
        btn_reboot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reboot.setFont(QFont("Google Sans", int(18 * self.scale), QFont.Weight.Bold))
        btn_reboot.setStyleSheet("""
            QPushButton { background-color: #2C2C35; color: white; border-radius: 12px; }
        """)
        btn_reboot.clicked.connect(self.reboot_system)
        layout.addWidget(btn_reboot)
        
        layout.addSpacing(int(10 * self.scale))

        btn_shutdown = QPushButton("⏻ Shutdown")
        btn_shutdown.setFixedHeight(int(75 * self.scale)) 
        btn_shutdown.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_shutdown.setFont(QFont("Google Sans", int(18 * self.scale), QFont.Weight.Bold))
        btn_shutdown.setStyleSheet("""
            QPushButton { background-color: #E24A4A; color: white; border-radius: 12px; }
        """)
        btn_shutdown.clicked.connect(self.shutdown_system)
        layout.addWidget(btn_shutdown)

        layout.addStretch()
        return page

    def update_scale_val(self, val):
        self.lbl_scale_val.setText(f"{val}%")

    def apply_scale_val(self):
        val = self.scale_slider.value()
        self.save_setting("app_drawer_scale", val)
        if hasattr(self.window(), 'rebuild_app_drawer'):
            self.window().rebuild_app_drawer()

    def set_app_layout(self, layout_type, save=True):
        active_style = """
            QPushButton { background-color: #5A8DEF; color: white; border-radius: 12px; }
        """
        inactive_style = """
            QPushButton { background-color: #2C2C35; color: white; border-radius: 12px; }
        """
        
        if layout_type == "grid":
            self.btn_grid.setStyleSheet(active_style)
            self.btn_list.setStyleSheet(inactive_style)
        else:
            self.btn_grid.setStyleSheet(inactive_style)
            self.btn_list.setStyleSheet(active_style)
            
        if save:
            self.save_setting("app_drawer_layout", layout_type)
            
        if hasattr(self.window(), 'rebuild_app_drawer'):
            self.window().rebuild_app_drawer()

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
            os.system("systemctl reboot")

    def shutdown_system(self):
        dialog = ModernDialog(self, "Shutdown System", "Are you sure you want to completely shut down?", "Shutdown")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            os.system("systemctl poweroff")