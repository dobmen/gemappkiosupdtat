import os
import urllib.request
import json
import time  # Used for CDN cache-busting
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QProgressBar, QMessageBox, QScroller
)

# Raw GitHub URL of your store manifest
MANIFEST_URL = "https://raw.githubusercontent.com/dobmen/gemappkiosstor/main/store_manifest.json"


class FetchManifestThread(QThread):
    """Background thread to fetch the app store catalog without freezing the UI."""
    on_success = pyqtSignal(list)
    on_error = pyqtSignal(str)

    def run(self):
        try:
            # Append a live timestamp query parameter to bypass GitHub's raw CDN cache
            cache_busting_url = f"{MANIFEST_URL}?t={int(time.time())}"
            
            req = urllib.request.Request(
                cache_busting_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Kiosk OS)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                self.on_success.emit(data.get("apps", []))
        except Exception as e:
            self.on_error.emit(str(e))


class DownloadAppThread(QThread):
    """Background thread to download an app script and icon from GitHub."""
    on_progress = pyqtSignal(int)
    on_finished = pyqtSignal(str)
    on_error = pyqtSignal(str)

    def __init__(self, app_data):
        super().__init__()
        self.app_data = app_data

    def run(self):
        try:
            self.on_progress.emit(10)
            
            # 1. Download the icon file into icons/
            icon_url = self.app_data["icon_url"]
            icon_filename = os.path.basename(icon_url)
            icon_path = os.path.join("icons", icon_filename)
            os.makedirs("icons", exist_ok=True)
            urllib.request.urlretrieve(icon_url, icon_path)
            self.on_progress.emit(50)

            # 2. Download to a .tmp file first for atomic updating
            os.makedirs("apps", exist_ok=True)
            temp_script = os.path.join("apps", "update.tmp")
            urllib.request.urlretrieve(self.app_data["script_url"], temp_script)
            self.on_progress.emit(80)
            
            # 3. Only replace the real file if download succeeds
            target_script = os.path.join("apps", self.app_data["filename"])
            os.replace(temp_script, target_script)
            
            # 4. Update the .ver companion file
            ver_path = target_script.replace(".py", ".ver")
            with open(ver_path, "w") as f:
                f.write(str(self.app_data["version"]))
            self.on_progress.emit(100)
                
            self.on_finished.emit(self.app_data["name"])
        except Exception as e:
            self.on_error.emit(f"Failed to install {self.app_data.get('name')}: {str(e)}")


class AppCard(QFrame):
    """A Google Play style card representing a single app from GitHub."""
    def __init__(self, app_data, install_callback):
        super().__init__()
        self.app_data = app_data
        self.install_callback = install_callback
        
        # Minimum height ensures multi-line descriptions don't get cut off
        self.setMinimumHeight(145)
        self.setStyleSheet("""
            AppCard {
                background-color: #1C1C22;
                border: 1px solid #2C2C35;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(15)

        # App Info Column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        lbl_name = QLabel(f"{app_data['name']} (v{app_data['version']})")
        lbl_name.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: white; border: none;")
        
        lbl_author = QLabel(f"By {app_data.get('author', 'Unknown')}")
        lbl_author.setFont(QFont("Google Sans", 12))
        lbl_author.setStyleSheet("color: #888888; border: none;")
        
        lbl_desc = QLabel(app_data['description'])
        lbl_desc.setFont(QFont("Google Sans", 14))
        lbl_desc.setStyleSheet("color: #CCCCCC; border: none;")
        lbl_desc.setWordWrap(True)

        info_layout.addWidget(lbl_name)
        info_layout.addWidget(lbl_author)
        info_layout.addWidget(lbl_desc)

        # 1. DETERMINE VERSION & INSTALL STATE FIRST
        local_script = os.path.join("apps", app_data["filename"])
        ver_path = local_script.replace(".py", ".ver")
        
        self.is_installed = os.path.exists(local_script)
        installed_version = "0.0.0"
        if os.path.exists(ver_path):
            with open(ver_path, "r") as f:
                installed_version = f.read().strip()
        
        self.needs_update = self.is_installed and (str(app_data["version"]) > installed_version)

        # 2. CREATE BUTTON USING THOSE STATES
        self.btn_install = QPushButton()
        self.btn_install.setFixedSize(130, 45)
        self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button_style()
        self.btn_install.clicked.connect(self.on_click)

        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.btn_install, alignment=Qt.AlignmentFlag.AlignVCenter)

    def update_button_style(self):
        """Cleanly sets the button styling based on install and update status."""
        if self.needs_update:
            self.btn_install.setText("⬆ Update")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #F39C12; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; }
                QPushButton:hover { background-color: #E67E22; }
            """)
        elif self.is_installed:
            self.btn_install.setText("Installed")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #2E2E38; color: #AAAAAA; border-radius: 8px; font-weight: bold; font-size: 15px; }
                QPushButton:hover { background-color: #383845; color: white; }
            """)
        else:
            self.btn_install.setText("⬇ Install")
            self.btn_install.setStyleSheet("""
                QPushButton { background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; font-size: 15px; }
                QPushButton:hover { background-color: #4A7DDF; }
            """)

    def on_click(self):
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Updating..." if self.needs_update else "Installing...")
        self.install_callback(self.app_data, self)


class AppStorePage(QWidget):
    """The Main App Store UI Module."""
    def __init__(self, on_install_success=None):
        super().__init__()
        self.on_install_success = on_install_success
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 30)
        layout.setSpacing(15)

        # Header Section
        header_layout = QHBoxLayout()
        title = QLabel("GitHub App Store")
        title.setFont(QFont("Google Sans", 26, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        
        btn_refresh = QPushButton("🔄 Refresh Catalog")
        btn_refresh.setFixedSize(160, 40)
        btn_refresh.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 8px; font-weight: bold;")
        btn_refresh.clicked.connect(self.load_catalog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        # Progress Bar for active downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1C1C22; border: none; } QProgressBar::chunk { background: #5A8DEF; }")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # SCROLLABLE STORE LIST WITH TOUCH SWIPE ENABLED
        # -------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Hide ugly desktop scrollbars for a clean mobile app look
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # =============================================================
        # NEW: ENABLE KINETIC TOUCH SWIPE SCROLLING!
        # =============================================================
        QScroller.grabGesture(
            self.scroll_area.viewport(), 
            QScroller.ScrollerGestureType.LeftMouseButtonGesture
        )
        
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(14)
        
        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area)

        # Initial fetch
        self.load_catalog()

    def load_catalog(self):
        """Clears current cards and fetches fresh data from GitHub."""
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        lbl_loading = QLabel("Fetching apps from GitHub repository...")
        lbl_loading.setFont(QFont("Google Sans", 16))
        lbl_loading.setStyleSheet("color: #888888; margin-top: 50px;")
        lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_loading)

        self.fetcher = FetchManifestThread()
        self.fetcher.on_success.connect(self.populate_catalog)
        self.fetcher.on_error.connect(self.show_error)
        self.fetcher.start()

    def populate_catalog(self, apps_list):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        if not apps_list:
            lbl_empty = QLabel("No apps found in the repository manifest.")
            lbl_empty.setStyleSheet("color: #AAAAAA; font-size: 16px;")
            self.list_layout.addWidget(lbl_empty)
            return

        for app_data in apps_list:
            card = AppCard(app_data, self.start_install)
            self.list_layout.addWidget(card)

    def show_error(self, error_msg):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)
        
        lbl_err = QLabel(f"Failed to connect to GitHub Repo:\n{error_msg}")
        lbl_err.setFont(QFont("Google Sans", 16))
        lbl_err.setStyleSheet("color: #E24A4A;")
        lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.addWidget(lbl_err)

    def start_install(self, app_data, card_reference):
        """Triggers background download of script and icon."""
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.downloader = DownloadAppThread(app_data)
        self.downloader.on_progress.connect(self.progress_bar.setValue)
        
        # Correctly pass BOTH app_data and card_reference!
        self.downloader.on_finished.connect(lambda name: self.on_install_complete(app_data, card_reference))
        
        self.downloader.on_error.connect(self.on_install_error)
        self.downloader.start()

    def on_install_complete(self, app_data, card):
        self.progress_bar.hide()
        
        # Update card properties and styling
        card.is_installed = True
        card.needs_update = False
        card.btn_install.setEnabled(True)
        card.update_button_style()
        
        # If kiosk.py passed a refresh function, trigger it!
        if self.on_install_success:
            self.on_install_success()
            
        QMessageBox.information(self, "Success", f"Successfully installed {app_data['name']} v{app_data['version']}!")

    def on_install_error(self, err_msg):
        self.progress_bar.hide()
        QMessageBox.warning(self, "Download Error", err_msg)
        self.load_catalog()