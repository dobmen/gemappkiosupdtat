import sys
import os
import time
import json
import importlib
import ssl
import urllib.request
import subprocess
import threading
from PyQt6.QtCore import Qt, QObject, pyqtProperty, pyqtSlot, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QThread
from PyQt6.QtWidgets import QWidget

class SystemUpdateCheckThread(QThread):
    update_detected = pyqtSignal(str)
    def run(self):
        try:
            local_version = "0.1.0"
            if os.path.exists("os_version.json"):
                with open("os_version.json", "r") as f:
                    local_version = json.load(f).get("version", "0.1.0")
            channel = "main"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = f"https://raw.githubusercontent.com/dobmen/gemappkiosupdtat/{channel}/os_version.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-Updater/1.0'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                remote_version = json.loads(response.read().decode('utf-8')).get("version", local_version)
                if remote_version != local_version:
                    self.update_detected.emit(remote_version)
        except Exception: pass

class AppStoreUpdateCheckThread(QThread):
    updates_detected = pyqtSignal(list)
    def run(self):
        try:
            installed_modules = []
            if os.path.exists("apps"):
                for filename in os.listdir("apps"):
                    if filename.endswith(".py") and filename not in ["__init__.py", "app_store.py", "local_music.py", "web_app.py", "settings.py", "gallery.py"]:
                        installed_modules.append(filename.replace(".py", ""))
            if not installed_modules: return
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = "https://raw.githubusercontent.com/dobmen/gemappkiosstor/main/store_manifest.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'KioskOS-AppUpdater/1.0'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                remote_apps = json.loads(response.read().decode('utf-8')).get("apps", [])
                remote_versions = {app["filename"].replace(".py", ""): app["version"] for app in remote_apps}
                apps_needing_update = []
                for app_id in installed_modules:
                    if app_id in remote_versions:
                        ver_path = os.path.join("apps", f"{app_id}.ver")
                        current_v = "0.0.0"
                        if os.path.exists(ver_path):
                            with open(ver_path, "r") as f: current_v = f.read().strip()
                        if remote_versions[app_id] > current_v:
                            apps_needing_update.append(app_id.replace("_", " ").title())
                if apps_needing_update:
                    self.updates_detected.emit(apps_needing_update)
        except Exception: pass

class KioskBackend(QObject):
    timeChanged = pyqtSignal()
    networkChanged = pyqtSignal()
    bluetoothChanged = pyqtSignal()
    dndChanged = pyqtSignal()
    silentChanged = pyqtSignal()
    brightnessChanged = pyqtSignal()
    volumeChanged = pyqtSignal()
    appsChanged = pyqtSignal()
    activeTasksChanged = pyqtSignal()
    notificationsChanged = pyqtSignal()
    activeClockfaceChanged = pyqtSignal()
    playBootVideo = pyqtSignal()
    
    appOpened = pyqtSignal(str)
    appMinimized = pyqtSignal()
    showToast = pyqtSignal(str, str, str, str)
    voiceListening = pyqtSignal()
    voiceUpdate = pyqtSignal(str)
    voiceHide = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_time = "12:00"
        self._network_enabled = self.get_system_setting("network_enabled", True)
        self._bluetooth_enabled = self.get_system_setting("bluetooth_enabled", False)
        self._dnd_enabled = self.get_system_setting("dnd_mode", False)
        self._silent_enabled = self.get_system_setting("silent_mode", False)
        self._brightness = 80
        self._volume = 50
        self._active_clockface = self.get_system_setting("clockface", "ClassicClock")
        self._clock_accent_color = self.get_system_setting("clock_accent", "#FFFFFF")
        self._apps = self.build_app_list()
        self._notifications = []
        
        self.running_apps = {}
        self._active_tasks = []
        
        if self.get_system_setting("just_updated", False) and os.path.exists("videos/update_boot.mp4"):
            self.save_system_setting("just_updated", False)
            QTimer.singleShot(500, self.playBootVideo.emit)

        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
        
        self.update_check_timer = QTimer(self)
        self.update_check_timer.timeout.connect(self.check_for_system_update)
        self.update_check_timer.start(86400000)
        QTimer.singleShot(5000, self.check_for_system_update)

        self.app_update_timer = QTimer(self)
        self.app_update_timer.timeout.connect(self.check_for_app_updates)
        self.app_update_timer.start(86400000)
        QTimer.singleShot(8000, self.check_for_app_updates)
        
        try:
            from components.voice_assistant import VoiceAssistantThread
            self.voice_thread = VoiceAssistantThread()
            self.voice_thread.command_recognized.connect(self.handle_voice_intent)
            self.voice_thread.wake_word_detected.connect(self.voiceListening)
            self.voice_thread.transcription_update.connect(self.voiceUpdate)
            self.voice_thread.sleep_mode.connect(self.voiceHide)
            self.voice_thread.start()
        except Exception as e:
            print("Could not start Voice Assistant:", e)

    def get_system_setting(self, key, default):
        try:
            if os.path.exists("os_version.json"):
                with open("os_version.json", "r") as f:
                    return json.load(f).get(key, default)
        except Exception:
            pass
        return default
        
    def save_system_setting(self, key, value):
        data = {}
        try:
            if os.path.exists("os_version.json"):
                with open("os_version.json", "r") as f:
                    data = json.load(f)
        except Exception:
            pass
        data[key] = value
        with open("os_version.json", "w") as f:
            json.dump(data, f, indent=4)

    def build_app_list(self):
        core_apps = [
            {"name": "App Store", "icon": "icons/appstore.png"},
            {"name": "Gallery", "icon": "icons/gallery.png"},
            {"name": "Local Music", "icon": "icons/music.png"}
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
                    downloaded_apps.append({"name": clean_name, "icon": icon_path})

        system_apps = [
            {"name": "Settings", "icon": "icons/settings.png"}
        ]

        seen = set()
        final_apps = []
        for app in core_apps + downloaded_apps + system_apps:
            if app["name"] not in seen:
                seen.add(app["name"])
                final_apps.append(app)
                
        return final_apps

    @pyqtProperty(str, notify=timeChanged)
    def currentTime(self):
        return self._current_time
        
    @pyqtProperty(list, notify=appsChanged)
    def apps(self):
        return self._apps
        
    @pyqtProperty(bool, notify=networkChanged)
    def networkEnabled(self):
        return self._network_enabled
        
    @pyqtProperty(bool, notify=bluetoothChanged)
    def bluetoothEnabled(self):
        return self._bluetooth_enabled
        
    @pyqtProperty(bool, notify=dndChanged)
    def dndEnabled(self): return self._dnd_enabled
        
    @pyqtProperty(bool, notify=silentChanged)
    def silentEnabled(self): return self._silent_enabled
        
    @pyqtProperty(int, notify=brightnessChanged)
    def brightness(self): return self._brightness
        
    @brightness.setter
    def brightness(self, value):
        if self._brightness != value:
            self._brightness = value
            self.brightnessChanged.emit()
            try:
                subprocess.Popen(["brightnessctl", "set", f"{value}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"[Hardware] Brightness error: {e}")

    @pyqtProperty(int, notify=volumeChanged)
    def volume(self): return self._volume
        
    @volume.setter
    def volume(self, value):
        if self._volume != value:
            self._volume = value
            self.volumeChanged.emit()
            try:
                subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{value}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"[Hardware] Volume error: {e}")
        
    @pyqtProperty(list, notify=notificationsChanged)
    def notifications(self): return self._notifications
        
    @pyqtProperty(str, notify=activeClockfaceChanged)
    def activeClockface(self): return self._active_clockface
        
    @activeClockface.setter
    def activeClockface(self, value):
        if self._active_clockface != value:
            self._active_clockface = value
            self.save_system_setting("clockface", value)
            self.activeClockfaceChanged.emit()

    @pyqtProperty(str, notify=activeClockfaceChanged)
    def clockAccentColor(self): return self._clock_accent_color
    
    @clockAccentColor.setter
    def clockAccentColor(self, color):
        if self._clock_accent_color != color:
            self._clock_accent_color = color
            self.save_system_setting("clock_accent", color)
            self.activeClockfaceChanged.emit()
        
    @pyqtProperty(list, notify=activeTasksChanged)
    def activeTasks(self):
        return self._active_tasks
        
    def _update_active_tasks(self):
        tasks = []
        for name in self.running_apps.keys():
            icon_path = ""
            safe_name = name.lower().replace(" ", "_")
            if os.path.exists(f"icons/{safe_name}.png"):
                icon_path = f"icons/{safe_name}.png"
            elif os.path.exists(f"icons/{safe_name}.svg"):
                icon_path = f"icons/{safe_name}.svg"
            tasks.append({"name": name, "icon": icon_path})
        self._active_tasks = tasks
        self.activeTasksChanged.emit()

    @pyqtSlot()
    def reloadApps(self):
        print("[QML Backend] Reloading apps list...")
        self._apps = self.build_app_list()
        self.appsChanged.emit()

    def update_time(self):
        new_time = time.strftime("%H:%M")
        if new_time != self._current_time:
            self._current_time = new_time
            self.timeChanged.emit()

    @pyqtSlot()
    def toggleNetwork(self):
        self._network_enabled = not self._network_enabled
        self.save_system_setting("network_enabled", self._network_enabled)
        self.networkChanged.emit()
        try:
            cmd = "on" if self._network_enabled else "off"
            subprocess.Popen(["nmcli", "radio", "wifi", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Hardware] Network error: {e}")
        
    @pyqtSlot()
    def toggleBluetooth(self):
        self._bluetooth_enabled = not self._bluetooth_enabled
        self.save_system_setting("bluetooth_enabled", self._bluetooth_enabled)
        self.bluetoothChanged.emit()
        try:
            cmd = "unblock" if self._bluetooth_enabled else "block"
            subprocess.Popen(["rfkill", cmd, "bluetooth"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Hardware] Bluetooth error: {e}")

    @pyqtSlot()
    def toggleDND(self):
        self._dnd_enabled = not self._dnd_enabled
        self.save_system_setting("dnd_mode", self._dnd_enabled)
        self.dndChanged.emit()
        
    @pyqtSlot()
    def toggleSilent(self):
        self._silent_enabled = not self._silent_enabled
        self.save_system_setting("silent_mode", self._silent_enabled)
        self.silentChanged.emit()
        
    @pyqtSlot()
    def clearNotifications(self):
        self._notifications.clear()
        self.notificationsChanged.emit()
        
    @pyqtSlot(int)
    def removeNotification(self, index):
        if 0 <= index < len(self._notifications):
            self._notifications.pop(index)
            self.notificationsChanged.emit()

    def add_notification(self, app, title, desc, icon="🔔"):
        self._notifications.insert(0, {"app": app, "title": title, "desc": desc, "icon": icon})
        self.notificationsChanged.emit()
        self.showToast.emit(app, title, desc, icon)
        
    def check_for_system_update(self):
        if hasattr(self, 'update_thread') and self.update_thread and self.update_thread.isRunning(): return
        self.update_thread = SystemUpdateCheckThread()
        self.update_thread.update_detected.connect(self.on_system_update_detected)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.start()

    def on_system_update_detected(self, new_version):
        if getattr(self, '_notified_update_version', None) == new_version: return
        self._notified_update_version = new_version
        self.add_notification("Settings", "System Update", "There is a new update available.", "⚙️")

    def check_for_app_updates(self):
        if hasattr(self, 'app_update_thread') and self.app_update_thread and self.app_update_thread.isRunning(): return
        self.app_update_thread = AppStoreUpdateCheckThread()
        self.app_update_thread.updates_detected.connect(self.on_app_updates_detected)
        self.app_update_thread.finished.connect(self.app_update_thread.deleteLater)
        self.app_update_thread.start()

    def on_app_updates_detected(self, apps_list):
        count = len(apps_list)
        desc = f"{count} app{'s' if count > 1 else ''} need updates."
        self.add_notification("App Store", "App Updates", desc, "📦")

    @pyqtSlot(str)
    def handle_voice_intent(self, intent):
        if intent == "close_app" or intent == "home":
            self.minimize_app()
        elif intent.startswith("launch_"):
            app = intent.replace("launch_", "").replace("_", " ").title()
            self.launch_app(app)

    @pyqtSlot()
    def minimize_app(self):
        print("[QML Backend] Minimizing active app")
        self.appMinimized.emit()
        for widget in self.running_apps.values():
            if widget.isVisible():
                widget.hide()

    @pyqtSlot(str)
    def kill_app(self, app_name):
        print(f"[QML Backend] Killing app: {app_name}")
        if app_name in self.running_apps:
            widget = self.running_apps.pop(app_name)
            widget.deleteLater()
            self._update_active_tasks()

    @pyqtSlot()
    def kill_all_apps(self):
        print("[QML Backend] Killing all apps")
        for widget in self.running_apps.values():
            widget.deleteLater()
        self.running_apps.clear()
        self._update_active_tasks()

    @pyqtSlot(str)
    def launch_app(self, app_name):
        print(f"[QML Backend] Launching app: {app_name}")
        if app_name in self.running_apps:
            widget = self.running_apps[app_name]
            widget.showFullScreen()
            widget.raise_()
            widget.activateWindow()
            return
            
        # Emit QML event instantly to start the 300ms fade-to-black animation unblocked
        self.appOpened.emit(app_name)
        
        # Completely delay the heavy Python import and window initialization by 350ms
        # so it doesn't freeze the QML rendering engine during the fade out!
        def do_launch():
            page_instance = None
            if app_name == "Local Music":
                try:
                    from apps.local_music import LocalMusicPage
                    page_instance = LocalMusicPage()
                except ImportError: pass
            elif app_name == "App Store":
                try:
                    from apps.app_store import AppStorePage
                    page_instance = AppStorePage(on_install_success=self.reloadApps)
                except ImportError: pass
            elif app_name == "Gallery":
                try:
                    from apps.gallery import GalleryPage
                    page_instance = GalleryPage(on_close=self.minimize_app)
                except ImportError: pass
            else:
                try:
                    module_name = app_name.lower().replace(" ", "_")
                    if os.path.exists(os.path.join("apps", f"{module_name}.py")):
                        mod = importlib.import_module(f"apps.{module_name}")
                        importlib.reload(mod)
                        
                        for attr_name in dir(mod):
                            if attr_name.endswith("Page") and attr_name not in ["AppStorePage", "LocalMusicPage", "GalleryPage"]:
                                page_class = getattr(mod, attr_name)
                                if isinstance(page_class, type) and issubclass(page_class, QWidget):
                                    try:
                                        page_instance = page_class(on_close=self.minimize_app)
                                    except TypeError:
                                        page_instance = page_class()
                                    break
                except Exception as e:
                    print(f"Error launching dynamic app '{app_name}': {e}")
                    
            if page_instance is not None:
                self.running_apps[app_name] = page_instance
                page_instance.showFullScreen()
                page_instance.raise_()
                page_instance.activateWindow()
                self._update_active_tasks()
                
        QTimer.singleShot(350, do_launch)

    @pyqtSlot()
    def shutdown(self):
        print("[QML Backend] Shutting down...")
        sys.exit(0)
