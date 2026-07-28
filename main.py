import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWebEngineWidgets import QWebEngineView  # Import early to share OpenGL contexts
from kiosk_backend import KioskBackend

print("[DEBUG] main.py: Starting execution in QML Mode")

class GlobalSwipeFilter(QObject):
    def __init__(self, backend, overlay):
        super().__init__()
        self.backend = backend
        self.overlay = overlay
        self.start_pos = None

    def eventFilter(self, obj, event):
        pos = None
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseMove):
            pos = event.globalPosition().toPoint()
        elif event.type() in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            if event.points():
                pos = event.points()[0].globalPosition().toPoint()
        
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.TouchBegin):
            if pos:
                self.start_pos = pos
        elif event.type() in (QEvent.Type.MouseMove, QEvent.Type.TouchUpdate):
            if self.start_pos and pos:
                    dx = pos.x() - self.start_pos.x()
                    dy = pos.y() - self.start_pos.y()
                    if self.start_pos.x() < 50 and self.backend.current_app_widget:
                        if dx > 10:
                            self.overlay.show()
                            self.overlay.update_pos(dx, pos.y())
                            
                    # Interactive swipe up
                    from PyQt6.QtGui import QGuiApplication
                    screen = QGuiApplication.primaryScreen().geometry()
                    if self.start_pos.y() > screen.height() - 50 and self.backend.current_app_widget:
                        if dy < -10:
                            app_widget = self.backend.current_app_widget
                            scale = max(0.5, 1.0 + (dy / screen.height()))
                            w = int(screen.width() * scale)
                            h = int(screen.height() * scale)
                            x = int(screen.width()/2 - w/2)
                            y = int(pos.y() - h/2) # center on finger roughly
                            app_widget.setGeometry(x, y, w, h)
        elif event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.TouchEnd):
            if self.start_pos and pos:
                    dx = pos.x() - self.start_pos.x()
                    dy = pos.y() - self.start_pos.y()
                    
                    if self.start_pos.x() < 50 and dx > 100 and self.backend.current_app_widget:
                        app_widget = self.backend.current_app_widget
                        if hasattr(app_widget, 'web') and hasattr(app_widget.web, 'back'):
                            app_widget.web.back()
                        else:
                            self.backend.minimize_app()
                            
                    # Screen height check for swipe up release
                    from PyQt6.QtGui import QGuiApplication
                    screen = QGuiApplication.primaryScreen().geometry()
                    if self.start_pos.y() > screen.height() - 50 and self.backend.current_app_widget:
                        if dy < -150:
                            self.backend.minimize_app()
                        else:
                            # Snap back to full screen
                            app_widget = self.backend.current_app_widget
                            app_widget.setGeometry(screen)
                        
            self.start_pos = None
            self.overlay.hide()
            
        return False

class GestureOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        self.resize(screen.width(), screen.height())
        self.move(0, 0)
        
        self.dx = 0
        self.y_pos = 0
        
    def update_pos(self, dx, y):
        self.dx = dx
        self.y_pos = y
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        x_pos = int(min(self.dx, 150) - 50)
        y_pos = int(self.y_pos - 50)
        
        if self.dx > 100:
            painter.setBrush(QColor(255, 255, 255, 200))
        else:
            painter.setBrush(QColor(255, 255, 255, 100))
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x_pos + 20, y_pos + 20, 60, 60)
        
        painter.setPen(QPen(QColor(0, 0, 0), 4))
        painter.drawLine(x_pos + 55, y_pos + 35, x_pos + 45, y_pos + 50)
        painter.drawLine(x_pos + 45, y_pos + 50, x_pos + 55, y_pos + 65)

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
    overlay = GestureOverlay()
    # Keep reference to avoid GC
    backend._gesture_overlay = overlay
    swipe_filter = GlobalSwipeFilter(backend, overlay)
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