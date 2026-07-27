import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtQml import QQmlApplicationEngine
from kiosk_backend import KioskBackend

print("[DEBUG] main.py: Starting execution in QML Mode")

class GlobalSwipeFilter(QObject):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.pressed_x = -1
        self.is_tracking = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(event, 'position') and event.position().x() < 50:
                self.pressed_x = event.position().x()
                self.is_tracking = True
            else:
                self.is_tracking = False
        elif event.type() == QEvent.Type.MouseMove:
            if self.is_tracking and hasattr(event, 'position'):
                if event.position().x() - self.pressed_x > 100:
                    self.is_tracking = False
                    self.backend.minimize_app()
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self.is_tracking = False
        return super().eventFilter(obj, event)

def main():
    # Enforce Wayland natively for QML hardware acceleration
    # os.environ["QT_QPA_PLATFORM"] = "wayland"
    
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    
    qml_errors = []
    def on_warnings(warnings):
        for w in warnings:
            qml_errors.append(w.toString())
    engine.warnings.connect(on_warnings)
    
    print("[DEBUG] main.py: Initializing QML Backend")
    backend = KioskBackend()
    
    # Install global swipe filter to catch edge-swipe-back over all Kiosk apps
    swipe_filter = GlobalSwipeFilter(backend)
    app.installEventFilter(swipe_filter)
    
    engine.rootContext().setContextProperty("backend", backend)
    
    qml_file = os.path.join(os.path.dirname(__file__), 'desktop.qml')
    print(f"[DEBUG] main.py: Loading {qml_file}")
    engine.load(qml_file)
    
    if not engine.rootObjects():
        print("[ERROR] main.py: Failed to load QML file!")
        print("\n".join(qml_errors))
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setWindowTitle("Fatal QML Error")
            msg.setText("Failed to start Kiosk OS. QML Errors:\n" + "\n".join(qml_errors))
            msg.exec()
        except:
            pass
        sys.exit(-1)
        
    print("[DEBUG] main.py: QML Engine started successfully!")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()