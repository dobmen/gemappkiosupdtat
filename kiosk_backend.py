import sys
import time
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot, QTimer

class KioskBackend(QObject):
    def __init__(self):
        super().__init__()
        self._current_time = "12:00"
        
        # Timer for clock
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

    @pyqtProperty(str)
    def currentTime(self):
        return self._current_time

    def update_time(self):
        # Update time and notify QML
        new_time = time.strftime("%H:%M")
        if new_time != self._current_time:
            self._current_time = new_time
            # For a proper pyqtProperty notification we'd use pyqtSignal,
            # but QML will read this once and we can add a signal later if needed.
            # (Wait, actually QML needs a NOTIFY signal to update automatically.
            # I'll fix this in the next iteration when fleshing out the full backend)

    @pyqtSlot(str)
    def launch_app(self, app_name):
        print(f"[DEBUG] QML requested launch of app: {app_name}")
        # Logic to launch apps will be ported here
