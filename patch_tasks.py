import re

with open('kiosk.py', 'r') as f:
    kiosk = f.read()

# Fix active task sizes
kiosk = kiosk.replace('lbl_icon.setFixedSize(32, 32)', 'lbl_icon.setFixedSize(int(32*SCALE_FACTOR), int(32*SCALE_FACTOR))')
kiosk = kiosk.replace('pix = QIcon(icon_path).pixmap(QSize(32, 32))', 'pix = QIcon(icon_path).pixmap(QSize(int(32*SCALE_FACTOR), int(32*SCALE_FACTOR)))')
kiosk = kiosk.replace('btn_kill.setFixedSize(32, 32)', 'btn_kill.setFixedSize(int(40*SCALE_FACTOR), int(40*SCALE_FACTOR))')
kiosk = kiosk.replace('btn_kill.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))', 'btn_kill.setFont(QFont("Google Sans", int(14*SCALE_FACTOR), QFont.Weight.Bold))')
kiosk = kiosk.replace('border-radius: 16px;', 'border-radius: {int(20*SCALE_FACTOR)}px;')

with open('kiosk.py', 'w') as f:
    f.write(kiosk)
print("tasks patched")
