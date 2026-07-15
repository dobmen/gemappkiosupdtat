import sys
from PyQt6.QtWidgets import QApplication
from kiosk import NestKiosk

def main():
    app = QApplication(sys.argv)
    
    # Initialize and display the main Kiosk OS window
    window = NestKiosk()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()