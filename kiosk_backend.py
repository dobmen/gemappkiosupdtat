import sys
import os
import time
import json
import importlib
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot, QTimer, pyqtSignal

class KioskBackend(QObject):
    timeChanged = pyqtSignal()
    networkChanged = pyqtSignal()
    bluetoothChanged = pyqtSignal()
    appsChanged = pyqtSignal()
    activeTasksChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_time = "12:00"
        self._network_enabled = self.get_system_setting("network_enabled", True)
        self._bluetooth_enabled = self.get_system_setting("bluetooth_enabled", False)
        self._apps = self.build_app_list()
        
        self.running_apps = {}
        self._active_tasks = []
        
        # Timer for clock
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

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
            {"name": "Settings", "icon": "icons/settings.svg"}
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
        
    @pyqtSlot()
    def toggleBluetooth(self):
        self._bluetooth_enabled = not self._bluetooth_enabled
        self.save_system_setting("bluetooth_enabled", self._bluetooth_enabled)
        self.bluetoothChanged.emit()

    @pyqtSlot()
    def minimize_app(self):
        print("[QML Backend] Minimizing active app")
        for widget in self.running_apps.values():
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
            
        page_instance = None
        
        if app_name == "Local Music":
            try:
                from apps.local_music import LocalMusicPage
                page_instance = LocalMusicPage()
            except ImportError: pass
        elif app_name == "App Store":
            try:
                from apps.app_store import AppStorePage
                page_instance = AppStorePage()
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

    @pyqtSlot()
    def shutdown(self):
        print("[QML Backend] Shutting down...")
        sys.exit(0)
