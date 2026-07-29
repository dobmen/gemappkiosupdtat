import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtWayland.Compositor

WaylandCompositor {
    id: compositor
    
    // The Wayland socket that apps will connect to (e.g. WAYLAND_DISPLAY=wayland-1)
    socketName: "wayland-1"

    WaylandOutput {
        sizeFollowsWindow: true
        window: Window {
            id: surfaceWindow
            width: 1280
            height: 720
            visible: true
            title: "Custom OS Wayland Compositor"
            color: "#000000"

            // OS Wallpaper
            Rectangle {
                id: backgroundRect
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#5A28FF" }
                    GradientStop { position: 1.0; color: "#101018" }
                }
            }

            ShaderEffectSource {
                id: bgSource
                sourceItem: backgroundRect
                visible: false
            }

            // Area to display Wayland Client Apps (like a calculator or browser)
            Item {
                id: clientArea
                anchors.fill: parent
                anchors.margins: 40 // Give apps some margin for the OS UI
            }

            // Top OS Status Bar
            Rectangle {
                width: parent.width
                height: 60
                color: "transparent"
                anchors.top: parent.top

                // The Custom GPU Blur Effect!
                ShaderEffect {
                    anchors.fill: parent
                    property variant source: bgSource
                    property size pixelSize: Qt.size(4.0 / parent.width, 4.0 / parent.height)
                    fragmentShader: "blur.frag.qsb"
                }
                
                Text {
                    anchors.centerIn: parent
                    text: "🌤️ Custom Wayland OS 🔋"
                    color: "white"
                    font.pixelSize: 18
                    font.bold: true
                }
            }
            
            // OS App Dock (Launcher)
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 20
                anchors.horizontalCenter: parent.horizontalCenter
                width: 300
                height: 80
                radius: 40
                color: "transparent"
                
                ShaderEffect {
                    anchors.fill: parent
                    property variant source: bgSource
                    property size pixelSize: Qt.size(4.0 / parent.width, 4.0 / parent.height)
                    fragmentShader: "blur.frag.qsb"
                }
                
                Text {
                    anchors.centerIn: parent
                    text: "App Dock Placeholder"
                    color: "white"
                }
            }
        }
    }

    // When an app (like Firefox or our Calculator) connects to the Wayland socket:
    Component {
        id: chromeComponent
        WaylandQuickItem {
            // This is the actual window buffer of the third-party app
            onSurfaceDestroyed: destroy()
            
            // Make the app window movable/draggable for multitasking
            MouseArea {
                anchors.fill: parent
                drag.target: parent
            }
        }
    }

    // Event handler for new Wayland surfaces
    onSurfaceCreated: (surface) => {
        var item = chromeComponent.createObject(clientArea, {
            "surface": surface
        });
    }
}
