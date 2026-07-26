print("[DEBUG] kiosk.py: Starting module load")
import os
print("[DEBUG] kiosk.py: Imported os")
import sys
print("[DEBUG] kiosk.py: Imported sys")
import json
print("[DEBUG] kiosk.py: Imported json")
import ssl
print("[DEBUG] kiosk.py: Imported ssl")
import time
print("[DEBUG] kiosk.py: Imported time")
import importlib
print("[DEBUG] kiosk.py: Imported importlib")
import urllib.request
print("[DEBUG] kiosk.py: Imported urllib")
print("[DEBUG] kiosk.py: About to import Qt modules...")
from PyQt6.QtCore import QDate, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QRect, Qt, QTime, QTimer, QThread, pyqtSignal, QPoint, QUrl, QSize
from PyQt6.QtGui import QFont, QFontDatabase, QPixmap, QPainter, QPainterPath, QColor, QGuiApplication, QIcon, QFontMetrics
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QMainWindow, 
    QPushButton, QSlider, QVBoxLayout, QWidget, QScrollArea, QScroller, QFrame, QSizePolicy, QGraphicsOpacityEffect, QGraphicsBlurEffect, QStackedWidget
)
print("[DEBUG] kiosk.py: Qt modules imported")

import subprocess
import threading
print("[DEBUG] kiosk.py: Imported subprocess and threading")

print("[DEBUG] kiosk.py: About to import custom modules (clockfaces, SlidingPanel)...")
# Import our custom modules dynamically for hot-swapping
import components.clockfaces as cf
from components import SlidingPanel
print("[DEBUG] kiosk.py: Imported clockfaces and SlidingPanel")

print("[DEBUG] kiosk.py: About to import LocalMusicPage...")
from apps.local_music import LocalMusicPage
print("[DEBUG] kiosk.py: Imported LocalMusicPage")

print("[DEBUG] kiosk.py: About to import create_web_app_view...")
from apps.web_app import create_web_app_view
print("[DEBUG] kiosk.py: Imported create_web_app_view")

print("[DEBUG] kiosk.py: About to import AppStorePage...")
from apps.app_store import AppStorePage
print("[DEBUG] kiosk.py: Imported AppStorePage")

print("[DEBUG] kiosk.py: About to import VoiceAssistantThread...")
from components.voice_assistant import VoiceAssistantThread
print("[DEBUG] kiosk.py: Module imports complete!")

# =================================================================
# 🖥️ DYNAMIC SCREEN & HARDWARE PROFILE ENGINE
# =================================================================
def get_screen_geometry():
    """Detects physical monitor resolution and classifies the hardware profile."""
    screen = QGuiApplication.primaryScreen()
    width, height = 1024, 600
    
    if screen:
        size = screen.size()
        width, height = size.width(), size.height()

    # Read Bash environment flag if available, otherwise classify by resolution
    env_mode = os.environ.get("KIOSK_DISPLAY_MODE", "")
    
    if width >= 1800 or env_mode == "WIDESCREEN_1200P":
        profile = "1920x1200 Widescreen Pro"
        default_cols = 6
    elif width <= 1280 or env_mode == "COMPACT_600P":
        profile = "1024x600 Compact Touch"
        default_cols = 4
    else:
        profile = f"{width}x{height} Custom Display"
        default_cols = 5 if width > 1400 else 4

    return width, height, profile, default_cols

# Dynamically evaluated at runtime boot
SCREEN_WIDTH, SCREEN_HEIGHT, DISPLAY_PROFILE, DEFAULT_GRID_COLS = get_screen_geometry()
SCALE_FACTOR = SCREEN_WIDTH / 1024.0
CC_HEIGHT = int(500 * (SCREEN_HEIGHT / 600.0))


def get_system_setting(key, default=None):
    """Fast, global helper to read user preferences dynamically."""
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                return config.get(key, default)
    except Exception:
        pass
    return default


def save_system_setting(key, value):
    """Fast, global helper to permanently save user preferences."""
    config = {}
    if os.path.exists("config.json"):
        try:
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


class SystemUpdateCheckThread(QThread):
    update_detected = pyqtSignal(str)

    def run(self):
        try:
            local_version = "0.1.0"
            if os.path.exists("os_version.json"):
                with open("os_version.json", "r") as f:
                    data = json.load(f)
                    local_version = data.get("version", "0.1.0")

            channel = get_system_setting("update_channel", "main")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = f"https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/{channel}/os_version.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-Updater/1.0'})
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                remote_data = json.loads(response.read().decode('utf-8'))
                remote_version = remote_data.get("version", local_version)
                
                if remote_version != local_version:
                    self.update_detected.emit(remote_version)
        except Exception:
            pass


class AppStoreUpdateCheckThread(QThread):
    updates_detected = pyqtSignal(list)

    def run(self):
        try:
            installed_modules = []
            if os.path.exists("apps"):
                for filename in os.listdir("apps"):
                    if filename.endswith(".py") and filename not in ["__init__.py", "app_store.py", "local_music.py", "web_app.py", "settings.py", "gallery.py"]:
                        installed_modules.append(filename.replace(".py", ""))

            if not installed_modules:
                return

            local_versions = {}
            if os.path.exists("apps_version.json"):
                with open("apps_version.json", "r") as f:
                    local_versions = json.load(f)

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://raw.githubusercontent.com/dobmen/gemappkiosstor/main/store_manifest.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-AppUpdater/1.0'})
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                manifest = json.loads(response.read().decode('utf-8'))
                remote_apps = manifest.get("apps", [])
                
                remote_versions = {app["filename"].replace(".py", ""): app["version"] for app in remote_apps}
                
                apps_needing_update = []
                for app_id in installed_modules:
                    if app_id in remote_versions:
                        local_script = os.path.join("apps", f"{app_id}.py")
                        ver_path = local_script.replace(".py", ".ver")
                        current_v = "0.0.0"
                        if os.path.exists(ver_path):
                            with open(ver_path, "r") as f:
                                current_v = f.read().strip()
                                
                        remote_v = remote_versions[app_id]
                        if remote_v > current_v:
                            clean_name = app_id.replace("_", " ").title()
                            apps_needing_update.append(clean_name)
                            
                if apps_needing_update:
                    self.updates_detected.emit(apps_needing_update)
        except Exception:
            pass


class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.offset = 0
        self.direction = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_offset)
        self.timer.start(50)
        
    def setText(self, text):
        super().setText(text)
        self.offset = 0
        self.direction = 1

    def update_offset(self):
        if not self.isVisible(): return
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())
        if text_width > self.width():
            self.offset += self.direction * 1
            if self.offset >= text_width - self.width() + 20:
                self.direction = -1
            elif self.offset <= -20:
                self.direction = 1
            self.update()
        else:
            self.offset = 0
            self.update()

    def paintEvent(self, event):
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())
        if text_width > self.width():
            painter = QPainter(self)
            painter.setPen(Qt.GlobalColor.white)
            path = QPainterPath()
            path.addRect(0, 0, self.width(), self.height())
            painter.setClipPath(path)
            rect = QRect(-self.offset, 0, text_width, self.height())
            painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
            painter.end()
        else:
            super().paintEvent(event)

class ToastNotification(QFrame):
    def __init__(self, parent, app_name, title, desc, icon_char, click_callback):
        super().__init__(parent)
        self.app_name = app_name
        self.click_callback = click_callback
        self.drag_start_x = None
        self.is_swiping = False
        
        toast_w = int(420 * SCALE_FACTOR)
        toast_h = int(85 * SCALE_FACTOR)
        radius = int(toast_h / 2)
        
        self.setFixedSize(toast_w, toast_h)
        self.setStyleSheet(f"background-color: #22222B; border-radius: {radius}px; border: 1px solid #33333F;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.center_x = (SCREEN_WIDTH - toast_w) // 2
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(int(15 * SCALE_FACTOR), int(10 * SCALE_FACTOR), int(25 * SCALE_FACTOR), int(10 * SCALE_FACTOR))
        layout.setSpacing(int(15 * SCALE_FACTOR))
        
        icon_size = int(54 * SCALE_FACTOR)
        lbl_icon = QLabel(icon_char)
        lbl_icon.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR)))
        lbl_icon.setFixedSize(icon_size, icon_size)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"background-color: rgba(255,255,255,10); border-radius: {icon_size//2}px; border: none;")
        
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Google Sans", int(15 * SCALE_FACTOR), QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        
        clean_desc = desc if len(desc) <= 35 else desc[:32] + "..."
        lbl_desc = QLabel(clean_desc)
        lbl_desc.setFont(QFont("Google Sans", int(13 * SCALE_FACTOR)))
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
        self.pos_anim.setStartValue(QPoint(self.center_x, -int(120 * SCALE_FACTOR)))
        self.pos_anim.setEndValue(QPoint(self.center_x, int(25 * SCALE_FACTOR)))
        self.pos_anim.start()
        self.hide_timer.start(4000)
        
    def dismiss(self):
        self.pos_anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.pos_anim.setStartValue(self.pos())
        self.pos_anim.setEndValue(QPoint(self.center_x, -int(120 * SCALE_FACTOR)))
        self.pos_anim.finished.connect(self.deleteLater)
        self.pos_anim.start()

    def swipe_dismiss(self, to_right):
        target_x = int(SCREEN_WIDTH + 200) if to_right else -int(SCREEN_WIDTH // 2)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pos_anim.setDuration(300)
        self.pos_anim.setStartValue(self.pos())
        self.pos_anim.setEndValue(QPoint(target_x, self.pos().y()))
        self.pos_anim.finished.connect(self.deleteLater)
        self.pos_anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_timer.stop() 
            self.drag_start_x = event.globalPosition().x()
            self.start_pos_x = self.pos().x()
            self.is_swiping = False

    def mouseMoveEvent(self, event):
        if self.drag_start_x is not None:
            dx = event.globalPosition().x() - self.drag_start_x
            if abs(dx) > 10:
                self.is_swiping = True
                self.move(int(self.start_pos_x + dx), self.pos().y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_swiping:
                dx = event.globalPosition().x() - self.drag_start_x
                if abs(dx) > 100:  
                    self.swipe_dismiss(dx > 0)
                else:  
                    self.pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)
                    self.pos_anim.setStartValue(self.pos())
                    self.pos_anim.setEndValue(QPoint(self.center_x, int(25 * SCALE_FACTOR)))
                    self.pos_anim.start()
                    self.hide_timer.start(4000)
            else:
                self.dismiss()
                if self.click_callback and self.app_name:
                    self.click_callback(self.app_name)
            self.drag_start_x = None
            self.is_swiping = False


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

        base_icon_size = int(72 * SCALE_FACTOR)
        base_font_size = int(14 * SCALE_FACTOR)
        
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
            layout.setContentsMargins(int(30 * SCALE_FACTOR), 15, int(30 * SCALE_FACTOR), 15)
            layout.setSpacing(25)
            self.setFixedHeight(icon_size + 40)
            
            layout.addWidget(lbl_icon)
            layout.addWidget(lbl_text)
            layout.addStretch() 

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.name)


class VoiceOverlay(QFrame):
    """Full-screen dimmed overlay for voice assistant feedback."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self.hide()
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon = QLabel("🎙️")
        self.icon.setFont(QFont("Google Sans", int(64 * SCALE_FACTOR)))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet("background: transparent; color: white;")
        
        self.lbl_text = QLabel("Listening...")
        self.lbl_text.setFont(QFont("Google Sans", int(36 * SCALE_FACTOR), QFont.Weight.Bold))
        self.lbl_text.setStyleSheet("color: white; background: transparent;")
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_text.setWordWrap(True)
        
        layout.addWidget(self.icon)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_text)

    def show_listening(self):
        self.lbl_text.setText("Listening...")
        self.raise_()
        self.show()

    def update_text(self, text):
        self.lbl_text.setText(text)


class NestKiosk(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- ANNOUNCE DETECTED HARDWARE ON BOOT ---
        print("=" * 50)
        print(f" [System Boot] Display Profile : {DISPLAY_PROFILE}")
        print(f" [System Boot] Resolution      : {SCREEN_WIDTH} x {SCREEN_HEIGHT}")
        print(f" [System Boot] UI Scale Multi  : {SCALE_FACTOR:.2f}x")
        print(f" [System Boot] Default Columns : {DEFAULT_GRID_COLS}")
        print("=" * 50)
        
        print("[DEBUG] Setting up fonts...")
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        if os.path.exists(font_dir):
            for filename in os.listdir(font_dir):
                if filename.endswith(".ttf") or filename.endswith(".otf"):
                    QFontDatabase.addApplicationFont(os.path.join(font_dir, filename))

        print("[DEBUG] Applying font to application...")
        app_font = QFont("Google Sans")
        QApplication.setFont(app_font)
        
        print("[DEBUG] Setting window size and flags...")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #0C0C0E; color: #FFFFFF;")

        print("[DEBUG] Setting up drag variables...")
        self.drag_start_pos = None
        self.active_gesture = None  
        self.running_apps = {} 
        self.current_toast = None
        self.empty_label = None
        
        print("[DEBUG] Initializing long press timer...")
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self.open_clockface_selector)

        print("[DEBUG] Setting up notification audio variables...")
        # Setup Notification Audio
        self.notif_sound_path = None
        print("[DEBUG] Getting sound path...")
        sound_path = os.path.abspath("notification.wav")
        print("[DEBUG] Checking if sound path exists...")
        if os.path.exists(sound_path):
            self.notif_sound_path = sound_path

        print("[DEBUG] Building main screen carousel widget...")
        # -------------------------------------------------------------
        # 1. MAIN SCREEN CAROUSEL & CLOCKFACE INJECTION
        # -------------------------------------------------------------
        self.main_carousel = QWidget(self)
        print("[DEBUG] Setting geometry for main carousel...")
        self.main_carousel.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

        self.home_index = 0
        self.home_pages = []
        
        print("[DEBUG] Creating page_clock widget...")
        self.page_clock = QWidget(self.main_carousel)
        self.page_clock.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.clock_layout = QVBoxLayout(self.page_clock)
        self.clock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_layout.setContentsMargins(0, 0, 0, 0)
        self.clock_layout.setSpacing(0)
        
        self.active_clock_widget = None
        print("[DEBUG] Applying clockface...")
        self.apply_clockface(get_system_setting("clockface_index", 0))
        print("[DEBUG] Clockface applied successfully")
        
        self.page_media = QWidget(self.main_carousel)
        self.page_media.setGeometry(SCREEN_WIDTH, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        media_layout = QVBoxLayout(self.page_media)
        media_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_media_title = QLabel("Now Playing")
        lbl_media_title.setFont(QFont("Google Sans", int(32 * SCALE_FACTOR), QFont.Weight.Bold))
        lbl_media_track = QLabel("No active stream • Swipe up to launch Spotify")
        lbl_media_track.setStyleSheet(f"color: #AAAAAA; font-size: {int(18 * SCALE_FACTOR)}px; margin-top: 10px;")
        media_layout.addWidget(lbl_media_title, alignment=Qt.AlignmentFlag.AlignCenter)
        media_layout.addWidget(lbl_media_track, alignment=Qt.AlignmentFlag.AlignCenter)

        self.home_pages.extend([self.page_clock, self.page_media])

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        # Blur effects are applied dynamically to prevent QPainter collisions

        self.indicator = QLabel("▲ Swipe up for apps", self)
        self.indicator.setGeometry(0, SCREEN_HEIGHT - int(40 * SCALE_FACTOR), SCREEN_WIDTH, int(40 * SCALE_FACTOR))
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indicator.setStyleSheet(f"color: #444444; font-size: {int(14 * SCALE_FACTOR)}px; font-weight: bold; background-color: transparent;")

        # -------------------------------------------------------------
        print("[DEBUG] Building quick settings panel...")
        # 2A. QUICK SETTINGS PANEL (Right Side)
        # -------------------------------------------------------------
        QS_WIDTH = int(SCREEN_WIDTH * 0.40)
        if QS_WIDTH < 350: QS_WIDTH = 350
        if QS_WIDTH > 500: QS_WIDTH = 500
        
        global CC_HEIGHT_MOD
        CC_HEIGHT_MOD = int(SCREEN_HEIGHT * 0.6)
        if CC_HEIGHT_MOD > 700: CC_HEIGHT_MOD = 700
        if CC_HEIGHT_MOD < 450: CC_HEIGHT_MOD = 450
        
        qs_x_pos = SCREEN_WIDTH - QS_WIDTH - int(20 * SCALE_FACTOR)
        self.control_center = SlidingPanel(self, 
            QRect(qs_x_pos, -CC_HEIGHT_MOD - 50, QS_WIDTH, CC_HEIGHT_MOD), 
            QRect(qs_x_pos, int(20 * SCALE_FACTOR), QS_WIDTH, CC_HEIGHT_MOD))
        
        self.control_center.setStyleSheet(f"""
            QWidget {{ background-color: rgba(30, 30, 35, 180); border-radius: {int(24 * SCALE_FACTOR)}px; border: 1px solid rgba(255, 255, 255, 20); }}
        """)
        
        cc_layout = QVBoxLayout(self.control_center)
        cc_layout.setContentsMargins(int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR))
        cc_layout.setSpacing(int(20 * SCALE_FACTOR))

        cc_header = QHBoxLayout()
        lbl_qs_title = QLabel("Quick Settings")
        lbl_qs_title.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR), QFont.Weight.Bold))
        lbl_qs_title.setStyleSheet("background: transparent; border: none; color: white;")
        cc_header.addWidget(lbl_qs_title)
        cc_header.addStretch()
        
        close_sys_btn = QPushButton("⏻")
        close_sys_btn.setFixedSize(int(44 * SCALE_FACTOR), int(44 * SCALE_FACTOR))
        close_sys_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_sys_btn.setStyleSheet(f"""
            QPushButton {{ background-color: rgba(226, 74, 74, 200); color: white; border-radius: {int(22 * SCALE_FACTOR)}px; font-size: {int(20 * SCALE_FACTOR)}px; border: none; }}
            QPushButton:pressed {{ background-color: rgba(200, 50, 50, 255); }}
        """)
        close_sys_btn.clicked.connect(self.close)
        cc_header.addWidget(close_sys_btn)
        cc_layout.addLayout(cc_header)

        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(int(20 * SCALE_FACTOR))
        
        b_container = QFrame()
        b_container.setStyleSheet(f"background-color: rgba(255, 255, 255, 15); border-radius: {int(24 * SCALE_FACTOR)}px; border: none;")
        b_layout = QVBoxLayout(b_container)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_b_icon = QLabel("☀️")
        lbl_b_icon.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR)))
        lbl_b_icon.setStyleSheet("background: transparent;")
        
        self.lbl_b_percent = QLabel("80%")
        self.lbl_b_percent.setFont(QFont("Google Sans", int(14 * SCALE_FACTOR), QFont.Weight.Bold))
        self.lbl_b_percent.setStyleSheet("color: white; background: transparent;")
        self.lbl_b_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.b_slider = QSlider(Qt.Orientation.Vertical)
        self.b_slider.setMinimumHeight(int(200 * SCALE_FACTOR))
        self.b_slider.setValue(80)
        self.b_slider.setStyleSheet(f"""
            QSlider::groove:vertical {{ background: rgba(0,0,0,80); width: {int(40 * SCALE_FACTOR)}px; border-radius: {int(20 * SCALE_FACTOR)}px; }}
            QSlider::handle:vertical {{ background: white; height: {int(40 * SCALE_FACTOR)}px; margin: 0; border-radius: {int(20 * SCALE_FACTOR)}px; }}
            QSlider::add-page:vertical {{ background: rgba(255, 255, 255, 220); border-radius: {int(20 * SCALE_FACTOR)}px; }}
        """)
        self.b_slider.valueChanged.connect(lambda v: self.lbl_b_percent.setText(f"{v}%"))
        
        b_layout.addWidget(self.lbl_b_percent, alignment=Qt.AlignmentFlag.AlignHCenter)
        b_layout.addSpacing(5)
        b_layout.addWidget(self.b_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        b_layout.addSpacing(10)
        b_layout.addWidget(lbl_b_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        sliders_layout.addWidget(b_container)

        v_container = QFrame()
        v_container.setStyleSheet(f"background-color: rgba(255, 255, 255, 15); border-radius: {int(24 * SCALE_FACTOR)}px; border: none;")
        v_layout = QVBoxLayout(v_container)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_v_icon = QLabel("🔊")
        lbl_v_icon.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR)))
        lbl_v_icon.setStyleSheet("background: transparent;")
        
        self.lbl_v_percent = QLabel("50%")
        self.lbl_v_percent.setFont(QFont("Google Sans", int(14 * SCALE_FACTOR), QFont.Weight.Bold))
        self.lbl_v_percent.setStyleSheet("color: white; background: transparent;")
        self.lbl_v_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.v_slider = QSlider(Qt.Orientation.Vertical)
        self.v_slider.setMinimumHeight(int(200 * SCALE_FACTOR))
        self.v_slider.setValue(50)
        self.v_slider.setStyleSheet(f"""
            QSlider::groove:vertical {{ background: rgba(0,0,0,80); width: {int(40 * SCALE_FACTOR)}px; border-radius: {int(20 * SCALE_FACTOR)}px; }}
            QSlider::handle:vertical {{ background: white; height: {int(40 * SCALE_FACTOR)}px; margin: 0; border-radius: {int(20 * SCALE_FACTOR)}px; }}
            QSlider::add-page:vertical {{ background: rgba(255, 255, 255, 220); border-radius: {int(20 * SCALE_FACTOR)}px; }}
        """)
        self.v_slider.valueChanged.connect(lambda v: self.lbl_v_percent.setText(f"{v}%"))
        
        v_layout.addWidget(self.lbl_v_percent, alignment=Qt.AlignmentFlag.AlignHCenter)
        v_layout.addSpacing(5)
        v_layout.addWidget(self.v_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        v_layout.addSpacing(10)
        v_layout.addWidget(lbl_v_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        sliders_layout.addWidget(v_container)
        
        cc_layout.addLayout(sliders_layout, stretch=1)
        
        # -------------------------------------------------------------
        print("[DEBUG] Building notifications panel...")
        # 2B. NOTIFICATIONS PANEL (Left Side)
        # -------------------------------------------------------------
        NOTIF_WIDTH = int(SCREEN_WIDTH * 0.45)
        if NOTIF_WIDTH < 450: NOTIF_WIDTH = 450
        if NOTIF_WIDTH > 650: NOTIF_WIDTH = 650
        
        notif_x_pos = int(20 * SCALE_FACTOR)
        self.notifs_panel = SlidingPanel(self, 
            QRect(notif_x_pos, -CC_HEIGHT_MOD - 50, NOTIF_WIDTH, CC_HEIGHT_MOD), 
            QRect(notif_x_pos, int(20 * SCALE_FACTOR), NOTIF_WIDTH, CC_HEIGHT_MOD))
        
        self.notifs_panel.setStyleSheet(f"""
            QWidget {{ background-color: rgba(30, 30, 35, 180); border-radius: {int(24 * SCALE_FACTOR)}px; border: 1px solid rgba(255, 255, 255, 20); }}
        """)
        
        notifs_main_layout = QVBoxLayout(self.notifs_panel)
        notifs_main_layout.setContentsMargins(int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR))
        
        notif_header = QHBoxLayout()
        self.lbl_notif_count = MarqueeLabel("Recent Alerts")
        self.lbl_notif_count.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR), QFont.Weight.Bold))
        self.lbl_notif_count.setStyleSheet("background: transparent; color: white; border: none;")
        self.lbl_notif_count.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        notif_header.addWidget(self.lbl_notif_count)
        notif_header.addStretch()

        btn_clear_notifs = QPushButton("Clear All")
        btn_clear_notifs.setFixedSize(int(100 * SCALE_FACTOR), int(36 * SCALE_FACTOR))
        btn_clear_notifs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear_notifs.setStyleSheet(f"background: rgba(255,255,255,40); color: white; border-radius: {int(18 * SCALE_FACTOR)}px; font-weight: bold; border: none;")
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
        self.notif_container.setStyleSheet("background: transparent; border: none;")
        self.notif_layout = QVBoxLayout(self.notif_container)
        self.notif_layout.setContentsMargins(0, int(20 * SCALE_FACTOR), 0, 0)
        self.notif_layout.setSpacing(int(16 * SCALE_FACTOR))
        self.notif_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.notif_scroll.setWidget(self.notif_container)
        notifs_main_layout.addWidget(self.notif_scroll, stretch=1)
        self.update_notif_header()

        # Override slide_in/out to include blur animation
        orig_cc_in = self.control_center.slide_in
        orig_cc_out = self.control_center.slide_out
        orig_nf_in = self.notifs_panel.slide_in
        orig_nf_out = self.notifs_panel.slide_out
        
        self._blur_animations = []
        def blur_in():
            self._blur_animations.clear()
            for widget in [self.main_carousel, getattr(self, 'app_stack', None)]:
                if not widget: continue
                effect = QGraphicsBlurEffect(widget)
                effect.setBlurRadius(0)
                widget.setGraphicsEffect(effect)
                anim = QPropertyAnimation(effect, b"blurRadius")
                anim.setDuration(300)
                anim.setEndValue(20)
                anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)
                self._blur_animations.append(anim)
                
        def blur_out():
            self._blur_animations.clear()
            for widget in [self.main_carousel, getattr(self, 'app_stack', None)]:
                if not widget: continue
                effect = widget.graphicsEffect()
                if effect:
                    anim = QPropertyAnimation(effect, b"blurRadius")
                    anim.setDuration(300)
                    anim.setEndValue(0)
                    anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
                    anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)
                    self._blur_animations.append(anim)

        def custom_cc_in(): orig_cc_in(); blur_in()
        def custom_cc_out(): orig_cc_out(); blur_out()
        def custom_nf_in(): orig_nf_in(); blur_in()
        def custom_nf_out(): orig_nf_out(); blur_out()

        self.control_center.slide_in = custom_cc_in
        self.control_center.slide_out = custom_cc_out
        self.notifs_panel.slide_in = custom_nf_in
        self.notifs_panel.slide_out = custom_nf_out

        # -------------------------------------------------------------
        print("[DEBUG] Building responsive app drawer...")
        # 3. RESPONSIVE APP DRAWER
        # -------------------------------------------------------------
        self.app_drawer = SlidingPanel(self, QRect(0, SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT), QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        self.app_drawer.setStyleSheet("background-color: #121215;")
        
        drawer_main_layout = QVBoxLayout(self.app_drawer)
        drawer_main_layout.setContentsMargins(0, int(30 * SCALE_FACTOR), 0, 0)
        drawer_main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(int(60 * SCALE_FACTOR), 0, int(60 * SCALE_FACTOR), 0)
        
        drawer_title = QLabel("Applications")
        drawer_title.setFont(QFont("Google Sans", int(26 * SCALE_FACTOR), QFont.Weight.Bold))
        header_layout.addWidget(drawer_title)
        header_layout.addStretch()

        self.multitask_btn_container = QWidget()
        self.multitask_btn_container.setFixedSize(int(170 * SCALE_FACTOR), int(48 * SCALE_FACTOR))
        self.multitask_btn_container.setStyleSheet("background: transparent;")

        self.btn_multitask = QPushButton("🗂️ Active Tasks", self.multitask_btn_container)
        self.btn_multitask.setGeometry(0, int(4 * SCALE_FACTOR), int(160 * SCALE_FACTOR), int(40 * SCALE_FACTOR))
        self.btn_multitask.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_multitask.setFont(QFont("Google Sans", int(13 * SCALE_FACTOR), QFont.Weight.Bold))
        self.btn_multitask.setStyleSheet("""
            QPushButton { background-color: #22222A; color: white; border: 1px solid #33333F; border-radius: 20px; }
            QPushButton:hover { background-color: #2E2E38; border-color: #4A4A5A; }
        """)
        self.btn_multitask.clicked.connect(self.toggle_task_ribbon)

        self.lbl_task_badge = QLabel("0", self.multitask_btn_container)
        self.lbl_task_badge.setGeometry(int(142 * SCALE_FACTOR), 0, int(24 * SCALE_FACTOR), int(24 * SCALE_FACTOR))
        self.lbl_task_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_task_badge.setFont(QFont("Google Sans", int(11 * SCALE_FACTOR), QFont.Weight.Bold))
        self.lbl_task_badge.setStyleSheet("""
            background-color: #3EA6FF; color: #0E0E12; border-radius: 12px; border: 2px solid #121215; font-weight: bold;
        """)
        self.lbl_task_badge.hide() 

        header_layout.addWidget(self.multitask_btn_container)
        drawer_main_layout.addLayout(header_layout)

        self.task_ribbon = QFrame()
        self.task_ribbon.setFixedHeight(int(120 * SCALE_FACTOR))
        self.task_ribbon.setStyleSheet("background-color: #1A1A22; border-top: 1px solid #2A2A35; border-bottom: 1px solid #2A2A35;")
        self.task_ribbon.hide()
        
        self.ribbon_layout = QHBoxLayout(self.task_ribbon)
        self.ribbon_layout.setContentsMargins(int(60 * SCALE_FACTOR), int(15 * SCALE_FACTOR), int(60 * SCALE_FACTOR), int(15 * SCALE_FACTOR))
        self.ribbon_layout.setSpacing(int(15 * SCALE_FACTOR))
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
        self.drawer_grid.setContentsMargins(int(60 * SCALE_FACTOR), int(20 * SCALE_FACTOR), int(60 * SCALE_FACTOR), int(100 * SCALE_FACTOR)) 
        self.drawer_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.drawer_scroll.setWidget(self.drawer_container)
        drawer_main_layout.addWidget(self.drawer_scroll)

        print("[DEBUG] Rebuilding app drawer content...")
        self.rebuild_app_drawer()
        print("[DEBUG] Boot complete. Showing window...")

        # -------------------------------------------------------------
        # 4. ACTIVE APP VIEW CONTAINER
        # -------------------------------------------------------------
        self.app_view = QWidget(self)
        self.app_view.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.app_view.hide()
        
        self.app_opacity = QGraphicsOpacityEffect(self.app_view)
        self.app_view.setGraphicsEffect(self.app_opacity)
        
        self.app_view_layout = QVBoxLayout(self.app_view)
        self.app_view_layout.setContentsMargins(0, 0, 0, 0)
        self.app_view_layout.setSpacing(0)
        
        self.app_stack = QStackedWidget()
        # App stack blur is handled dynamically
        
        self.app_view_layout.addWidget(self.app_stack)

        self.anim_app_group = QParallelAnimationGroup()
        self.anim_app_geom = QPropertyAnimation(self.app_view, b"geometry")
        self.anim_app_fade = QPropertyAnimation(self.app_opacity, b"opacity")
        self.anim_app_group.addAnimation(self.anim_app_geom)
        self.anim_app_group.addAnimation(self.anim_app_fade)

        self.edge_interceptor = QWidget(self)
        self.edge_interceptor.setGeometry(0, 0, int(25 * SCALE_FACTOR), SCREEN_HEIGHT)
        self.edge_interceptor.setStyleSheet("background-color: transparent;")
        self.edge_interceptor.raise_() 
        
        self.selector_overlay = cf.ClockSelectorOverlay(self, self.apply_clockface)

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

        # -------------------------------------------------------------
        # 6. VOICE ASSISTANT BACKGROUND WORKER & VISUAL OVERLAY
        # -------------------------------------------------------------
        self.voice_overlay = VoiceOverlay(self)
        
        self.voice_thread = VoiceAssistantThread()
        self.voice_thread.command_recognized.connect(self.handle_voice_intent)
        self.voice_thread.wake_word_detected.connect(self.voice_overlay.show_listening)
        self.voice_thread.transcription_update.connect(self.voice_overlay.update_text)
        self.voice_thread.sleep_mode.connect(self.voice_overlay.hide)
        
        self.voice_thread.start()

    def show_toast(self, app_name, title, desc, icon):
        dnd_mode = get_system_setting("dnd_mode", False)
        if dnd_mode: return  
            
        try:
            if getattr(self, 'current_toast', None):
                self.current_toast.deleteLater()
        except RuntimeError: pass
            
        silent_mode = get_system_setting("silent_mode", False)
        if getattr(self, 'notif_sound_path', None) and not silent_mode:
            def play_sound():
                try:
                    if sys.platform == "darwin":
                        subprocess.run(['afplay', self.notif_sound_path], check=False)
                    else:
                        subprocess.run(['aplay', '-q', self.notif_sound_path], check=False)
                except Exception:
                    pass
            threading.Thread(target=play_sound, daemon=True).start()
            
        self.current_toast = ToastNotification(self, app_name, title, desc, icon, self.launch_app)
        self.current_toast.show_toast()

    def update_clock(self):
        t = QTime.currentTime()
        d = QDate.currentDate()
        if self.active_clock_widget:
            self.active_clock_widget.update_time(t, d)
        if hasattr(self, 'selector_overlay'):
            self.selector_overlay.update_time(t, d)

    def apply_clockface(self, idx):
        if idx >= len(cf.CLOCKFACE_CLASSES) or idx < 0:
            idx = 0
            
        if self.active_clock_widget:
            self.active_clock_widget.setParent(None)
            self.active_clock_widget.deleteLater()
            
        self.active_clock_widget = cf.CLOCKFACE_CLASSES[idx]()
        self.clock_layout.addWidget(self.active_clock_widget)
        save_system_setting("clockface_index", idx)
        self.update_clock()

    def open_clockface_selector(self):
        self.long_press_timer.stop()
        current_idx = get_system_setting("clockface_index", 0)
        self.selector_overlay.show_selector(current_idx)

    # =================================================================
    # KEYBOARD & DEBUG EVENTS
    # =================================================================
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backslash:
            self.take_screenshot()
        super().keyPressEvent(event)

    def take_screenshot(self):
        try:
            os.makedirs("screenshots", exist_ok=True)
            timestamp = int(time.time())
            
            app_name = "kiosk"
            if not self.app_view.isHidden():
                for name, widget in self.running_apps.items():
                    if self.app_stack.currentWidget() == widget:
                        app_name = name.lower().replace(" ", "_")
                        break

            filename = f"screenshots/{app_name}_{timestamp}.png"
            pixmap = self.grab()
            pixmap.save(filename, "PNG")
            
            self.show_toast("App Store", "Screenshot Saved", f"Saved to {filename}", "📸")
        except Exception as e:
            print(f"Screenshot error: {e}")

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

        while self.ribbon_layout.count():
            item = self.ribbon_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget(): sub.widget().deleteLater()

        for app_name in list(self.running_apps.keys()):
            card = QFrame()
            card.setFixedSize(int(220 * SCALE_FACTOR), int(75 * SCALE_FACTOR))
            card.setStyleSheet("background-color: #24242E; border-radius: 12px; border: 1px solid #333340;")
            
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 10, 8)
            card_layout.setSpacing(10)
            
            # Fetch icon if available
            icon_path = ""
            safe_name = app_name.lower().replace(" ", "_")
            if os.path.exists(f"icons/{safe_name}.png"):
                icon_path = f"icons/{safe_name}.png"
            elif os.path.exists(f"icons/{safe_name}.svg"):
                icon_path = f"icons/{safe_name}.svg"
            
            if icon_path:
                lbl_icon = QLabel()
                pix = QIcon(icon_path).pixmap(QSize(32, 32))
                lbl_icon.setPixmap(pix)
                lbl_icon.setFixedSize(32, 32)
                card_layout.addWidget(lbl_icon)
            
            btn_switch = QPushButton(app_name)
            btn_switch.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_switch.setFont(QFont("Google Sans", int(14 * SCALE_FACTOR), QFont.Weight.Bold))
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
            ("Gallery", "icons/gallery.png"),
            ("Local Music", "icons/music.png")
        ]

        downloaded_apps = []
        if os.path.exists("apps"):
            for filename in sorted(os.listdir("apps")):
                if filename.endswith(".py") and filename not in ["__init__.py", "app_store.py", "local_music.py", "web_app.py", "settings.py", "gallery.py"]:
                    clean_name = filename.replace(".py", "").replace("_", " ").title()
                    png_name = filename.replace(".py", ".png")
                    svg_name = filename.replace(".py", ".svg")
                    
                    if os.path.exists(os.path.join("icons", png_name)):
                        icon_path = os.path.join("icons", png_name)
                    else:
                        icon_path = os.path.join("icons", svg_name)
                    downloaded_apps.append((clean_name, icon_path))

        system_apps = [
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
            self.drawer_grid.setSpacing(int(35 * SCALE_FACTOR)) 
            # Automatically apply 4 columns for 1024x600 or 6 columns for 1920x1200
            columns = max(1, int(DEFAULT_GRID_COLS * (100.0 / scale)))
            if columns > 8: columns = 8
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

            if self.home_index == 0 and self.app_view.isHidden() and not self.control_center.is_visible and not self.notifs_panel.is_visible and not self.app_drawer.is_visible:
                self.long_press_timer.start(700) 

            if not self.app_view.isHidden() and self.drag_start_pos.x() <= int(50 * SCALE_FACTOR):
                self.active_gesture = 'edge_swipe_back'

    def mouseMoveEvent(self, event):
        if not self.drag_start_pos:
            return

        current_pos = event.position().toPoint()
        dx = current_pos.x() - self.drag_start_pos.x()
        dy = current_pos.y() - self.drag_start_pos.y()

        if abs(dx) > 10 or abs(dy) > 10:
            self.long_press_timer.stop()

        if self.active_gesture is None and (abs(dx) > 15 or abs(dy) > 15):
            if abs(dy) > abs(dx):
                if self.app_drawer.is_visible:
                    if dy > 0: self.active_gesture = 'close_drawer'
                elif self.control_center.is_visible:
                    if dy < 0: self.active_gesture = 'close_controls'
                elif self.notifs_panel.is_visible:
                    if dy < 0: self.active_gesture = 'close_notifs'
                elif self.app_view.isHidden():
                    if dy < 0:
                        self.active_gesture = 'open_drawer'
                        self.app_drawer.raise_()
                    elif dy > 0:
                        if self.drag_start_pos.x() >= SCREEN_WIDTH / 2:
                            self.active_gesture = 'open_controls'
                            self.control_center.raise_()
                        else:
                            self.active_gesture = 'open_notifs'
                            self.notifs_panel.raise_()
            else:
                if not self.app_drawer.is_visible and not self.control_center.is_visible and not self.notifs_panel.is_visible and self.app_view.isHidden():
                    self.active_gesture = 'horizontal'

        if self.active_gesture == 'edge_swipe_back':
            new_x = max(0, min(SCREEN_WIDTH, dx))
            self.app_view.move(new_x, 0)
        elif self.active_gesture == 'open_drawer':
            new_y = max(0, min(SCREEN_HEIGHT, SCREEN_HEIGHT + dy))
            self.app_drawer.move(0, new_y)
        elif self.active_gesture == 'close_drawer':
            new_y = max(0, min(SCREEN_HEIGHT, dy))
            self.app_drawer.move(0, new_y)
        elif self.active_gesture in ('open_controls', 'open_notifs', 'close_controls', 'close_notifs'):
            target_panel = self.control_center if 'controls' in self.active_gesture else self.notifs_panel
            if 'open' in self.active_gesture:
                new_y = max(-CC_HEIGHT_MOD, min(0, -CC_HEIGHT_MOD + dy))
            else:
                new_y = max(-CC_HEIGHT_MOD, min(0, dy))
            
            target_panel.move(target_panel.x(), new_y)
            progress = (new_y + CC_HEIGHT_MOD) / CC_HEIGHT_MOD
            blur_val = int(20 * progress)
            if blur_val > 0:
                effect1 = self.main_carousel.graphicsEffect()
                if not effect1:
                    effect1 = QGraphicsBlurEffect(self.main_carousel)
                    self.main_carousel.setGraphicsEffect(effect1)
                effect1.setBlurRadius(blur_val)
                
                if hasattr(self, 'app_stack'):
                    effect2 = self.app_stack.graphicsEffect()
                    if not effect2:
                        effect2 = QGraphicsBlurEffect(self.app_stack)
                        self.app_stack.setGraphicsEffect(effect2)
                    effect2.setBlurRadius(blur_val)
            else:
                self.main_carousel.setGraphicsEffect(None)
                if hasattr(self, 'app_stack'): 
                    self.app_stack.setGraphicsEffect(None)
        elif self.active_gesture == 'horizontal':
            current_page = self.home_pages[self.home_index]
            current_page.move(dx, 0)
            if dx < 0 and self.home_index < len(self.home_pages) - 1:
                next_page = self.home_pages[self.home_index + 1]
                next_page.show()
                next_page.move(SCREEN_WIDTH + dx, 0)
            elif dx > 0 and self.home_index > 0:
                prev_page = self.home_pages[self.home_index - 1]
                prev_page.show()
                prev_page.move(-SCREEN_WIDTH + dx, 0)

    def mouseReleaseEvent(self, event):
        self.long_press_timer.stop()
        
        if not self.drag_start_pos or not self.active_gesture:
            self.drag_start_pos = None
            return

        current_pos = event.position().toPoint()
        dx = current_pos.x() - self.drag_start_pos.x()
        dy = current_pos.y() - self.drag_start_pos.y()

        if self.active_gesture == 'edge_swipe_back':
            if dx > int(150 * SCALE_FACTOR): self.animate_app_close()
            else:        self.animate_app_snap_back()
        elif self.active_gesture == 'open_drawer':
            if dy < -int(120 * SCALE_FACTOR): 
                self.app_drawer.slide_in()
            else:         
                self.app_drawer.slide_out()
        elif self.active_gesture in ('open_controls', 'open_notifs'):
            target_panel = self.control_center if self.active_gesture == 'open_controls' else self.notifs_panel
            if dy > int(120 * SCALE_FACTOR): target_panel.slide_in()
            else: target_panel.slide_out()
        elif self.active_gesture == 'close_drawer':
            if dy > int(120 * SCALE_FACTOR):  self.app_drawer.slide_out()
            else:         self.app_drawer.slide_in()
        elif self.active_gesture in ('close_controls', 'close_notifs'):
            target_panel = self.control_center if self.active_gesture == 'close_controls' else self.notifs_panel
            if dy < -int(120 * SCALE_FACTOR): target_panel.slide_out()
            else: target_panel.slide_in()
        elif self.active_gesture == 'horizontal':
            current_page = self.home_pages[self.home_index]
            if dx < -int(200 * SCALE_FACTOR) and self.home_index < len(self.home_pages) - 1:
                next_page = self.home_pages[self.home_index + 1]
                self.animate_carousel(current_page, QRect(-SCREEN_WIDTH, 0, SCREEN_WIDTH, SCREEN_HEIGHT), next_page, QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), self.home_index + 1)
            elif dx > int(200 * SCALE_FACTOR) and self.home_index > 0:
                prev_page = self.home_pages[self.home_index - 1]
                self.animate_carousel(current_page, QRect(SCREEN_WIDTH, 0, SCREEN_WIDTH, SCREEN_HEIGHT), prev_page, QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), self.home_index - 1)
            else:
                self.animate_carousel(current_page, QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
                if self.home_index < len(self.home_pages) - 1:
                    self.home_pages[self.home_index + 1].move(SCREEN_WIDTH, 0)
                if self.home_index > 0:
                    self.home_pages[self.home_index - 1].move(-SCREEN_WIDTH, 0)

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
                self.home_index = new_index

    # =================================================================
    # VOICE ASSISTANT ROUTING
    # =================================================================
    def handle_voice_intent(self, intent, argument):
        """Executes hot-swapped UI commands triggered by voice thread signals."""
        print(f"[Core Router] Executing voice intent: {intent} ({argument})")
        
        if intent == "launch_app":
            self.launch_app(argument)
            self.show_toast("Voice Assistant", f"Launched App", f"Opened {argument}", "🎙️")
            
        elif intent == "close_app":
            self.minimize_app()
            
        elif intent == "change_clock":
            idx = int(argument)
            self.apply_clockface(idx)
            if hasattr(self, 'selector_overlay'):
                self.selector_overlay.current_idx = idx
            self.show_toast("Voice Assistant", "Changed Watchface", "New clock layout applied", "🎙️")
                
        elif intent == "system":
            if argument == "reboot":
                os.system("systemctl reboot")
            elif argument == "shutdown":
                os.system("systemctl poweroff")

    def closeEvent(self, event):
        if hasattr(self, 'voice_thread'):
            self.voice_thread.stop()
            self.voice_thread.wait()
        super().closeEvent(event)

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
            if app_name == "Local Music":
                page_instance = LocalMusicPage()
            elif app_name == "App Store":
                page_instance = AppStorePage()
            elif app_name == "Gallery":
                from apps.gallery import GalleryPage
                page_instance = GalleryPage(on_close=self.minimize_app)
            else:
                loaded_successfully = False
                try:
                    module_name = app_name.lower().replace(" ", "_")
                    if os.path.exists(os.path.join("apps", f"{module_name}.py")):
                        mod = importlib.import_module(f"apps.{module_name}")
                        importlib.reload(mod) 
                        
                        for attr_name in dir(mod):
                            if attr_name.endswith("Page") and attr_name not in ["AppStorePage", "LocalMusicPage", "GalleryPage"]:
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
                    app_title.setFont(QFont("Google Sans", int(32 * SCALE_FACTOR), QFont.Weight.Bold))
                    desc = QLabel("Swipe from the far left edge of the screen to return home.")
                    desc.setStyleSheet(f"color: #888888; font-size: {int(16 * SCALE_FACTOR)}px; margin-top: 10px;")
                    layout.addWidget(app_title, alignment=Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter)
                    
                    btn_close = QPushButton("Return Home")
                    btn_close.setFixedSize(int(200 * SCALE_FACTOR), int(50 * SCALE_FACTOR))
                    btn_close.setStyleSheet("background-color: #E24A4A; border-radius: 10px; color: white;")
                    btn_close.clicked.connect(self.minimize_app)
                    layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
                    
                    page_instance = app_box

            self.app_stack.addWidget(page_instance)
            self.running_apps[app_name] = page_instance
            self.app_stack.setCurrentWidget(page_instance)
            self.update_task_switcher()

        start_rect = QRect(int(SCREEN_WIDTH * 0.075), int(SCREEN_HEIGHT * 0.075), int(SCREEN_WIDTH * 0.85), int(SCREEN_HEIGHT * 0.85))
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
        self.anim_app_geom.setEndValue(QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        
        self.anim_app_fade.setDuration(250)
        self.anim_app_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_app_fade.setStartValue(0.0)
        self.anim_app_fade.setEndValue(1.0)
        
        self.anim_app_group.start()

    def animate_app_close(self):
        self.anim_app_group.stop()
        
        end_rect = QRect(int(SCREEN_WIDTH * 0.075), int(SCREEN_HEIGHT * 0.075), int(SCREEN_WIDTH * 0.85), int(SCREEN_HEIGHT * 0.85))
        
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
        self.anim_app_geom.setEndValue(QRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        
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