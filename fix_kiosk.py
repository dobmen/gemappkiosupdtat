import re

with open('kiosk.py', 'r') as f:
    content = f.read()

# Find LongPressButton block
long_press_pattern = re.compile(
    r'# =================================================================\n'
    r'# 🖥️ HARDWARE BUTTONS & UI COMPONENTS\n'
    r'# =================================================================\n'
    r'class LongPressButton\(QPushButton\):\n'
    r'(?:    (?:def |[^\n]*\n|\n)+?)(?=    # =================================================================\n)'
)

match = long_press_pattern.search(content)
if match:
    block = match.group(0)
    print("Found block!")
    
    # Remove block
    content = content.replace(block, "")
    
    # Insert block after all the imports, right before NestKiosk starts
    insert_point = content.find("class NestKiosk(QMainWindow):")
    if insert_point != -1:
        content = content[:insert_point] + block + "\n" + content[insert_point:]
        
        with open('kiosk.py', 'w') as f:
            f.write(content)
        print("Fixed kiosk.py!")
else:
    print("Could not find LongPressButton block.")
