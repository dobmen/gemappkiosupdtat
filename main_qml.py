import sys
import os
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from kiosk_backend import KioskBackend

def main():
    # Enforce Wayland
    os.environ["QT_QPA_PLATFORM"] = "wayland"
    
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    
    backend = KioskBackend()
    engine.rootContext().setContextProperty("backend", backend)
    
    qml_file = os.path.join(os.path.dirname(__file__), 'desktop.qml')
    engine.load(qml_file)
    
    if not engine.rootObjects():
        sys.exit(-1)
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
