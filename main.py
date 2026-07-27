import sys
import os
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from kiosk_backend import KioskBackend

print("[DEBUG] main.py: Starting execution in QML Mode")

def main():
    # Enforce Wayland natively for QML hardware acceleration
    # os.environ["QT_QPA_PLATFORM"] = "wayland"
    
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    
    print("[DEBUG] main.py: Initializing QML Backend")
    backend = KioskBackend()
    engine.rootContext().setContextProperty("backend", backend)
    
    qml_file = os.path.join(os.path.dirname(__file__), 'desktop.qml')
    print(f"[DEBUG] main.py: Loading {qml_file}")
    engine.load(qml_file)
    
    if not engine.rootObjects():
        print("[ERROR] main.py: Failed to load QML file!")
        sys.exit(-1)
        
    print("[DEBUG] main.py: QML Engine started successfully!")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()