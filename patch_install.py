with open('install.sh', 'r') as f:
    content = f.read()

content = content.replace("openbox x11-utils x11-xserver-utils xinput picom", "labwc wlr-randr wayland-protocols")
content = content.replace("xinput", "")

with open('install.sh', 'w') as f:
    f.write(content)
print("install.sh patched")
