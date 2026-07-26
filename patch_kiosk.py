import re

with open('kiosk.py', 'r') as f:
    kiosk = f.read()

# Fix Notifs panel widths
kiosk = kiosk.replace("if NOTIF_WIDTH > 650: NOTIF_WIDTH = 650", "if NOTIF_WIDTH > int(800 * SCALE_FACTOR): NOTIF_WIDTH = int(800 * SCALE_FACTOR)")
kiosk = kiosk.replace("if NOTIF_WIDTH < 450: NOTIF_WIDTH = 450", "if NOTIF_WIDTH < int(450 * SCALE_FACTOR): NOTIF_WIDTH = int(450 * SCALE_FACTOR)")

# Fix Control Center widths
kiosk = kiosk.replace("if QS_WIDTH > 500: QS_WIDTH = 500", "if QS_WIDTH > int(700 * SCALE_FACTOR): QS_WIDTH = int(700 * SCALE_FACTOR)")
kiosk = kiosk.replace("if QS_WIDTH < 350: QS_WIDTH = 350", "if QS_WIDTH < int(350 * SCALE_FACTOR): QS_WIDTH = int(350 * SCALE_FACTOR)")

# Fix titles
kiosk = kiosk.replace('self.lbl_notif_count.setFont(QFont("Google Sans", int(24 * SCALE_FACTOR), QFont.Weight.Bold))', 'self.lbl_notif_count.setFont(QFont("Google Sans", int(18 * SCALE_FACTOR), QFont.Weight.Bold))')
kiosk = kiosk.replace('lbl_qs_title.setFont(QFont("Google Sans", int(20 * SCALE_FACTOR), QFont.Weight.Bold))', 'lbl_qs_title.setFont(QFont("Google Sans", int(16 * SCALE_FACTOR), QFont.Weight.Bold))')

# Fix controls font sizes in control panel (both conn and mode buttons)
kiosk = re.sub(r'font-size: \{int\(16 \* SCALE_FACTOR\)\}px;', r'font-size: {int(13 * SCALE_FACTOR)}px;', kiosk)

# Fix Close Button in active tasks (Wait, we need to check what the close button is)
# It's probably `btn_close.setFixedSize(30, 30)` or something. Let's find it.
# Actually I'll do this in a separate step or add it now if I know the exact string.

with open('kiosk.py', 'w') as f:
    f.write(kiosk)
print("kiosk.py patched")
