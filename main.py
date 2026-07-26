print("[DEBUG] main.py: Starting execution")
import sys
print("[DEBUG] main.py: Imported sys")
from PyQt6.QtWidgets import QApplication
print("[DEBUG] main.py: Imported QApplication")
print("[DEBUG] main.py: About to import NestKiosk from kiosk.py")
from kiosk import NestKiosk
print("[DEBUG] main.py: Imported NestKiosk successfully")

def main():
    app = QApplication(sys.argv)
    
    # Initialize and display the main Kiosk OS window
    window = NestKiosk()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()