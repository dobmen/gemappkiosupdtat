import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 1920
    title: "Kiosk OS"
    
    // Transparent background for true Wayland overlay (if supported)
    color: "#0C0C0E"

    // The backend bridge
    // backend property will be injected from Python via QQmlApplicationEngine
    
    // Main content area (App Drawer, Clock, etc.)
    SwipeView {
        id: swipeView
        anchors.fill: parent
        currentIndex: 1 // Start on the middle page (Clock)
        
        // Page 0: App Drawer
        Item {
            id: appDrawerPage
            Rectangle {
                anchors.fill: parent
                color: "#181825"
                Text {
                    anchors.centerIn: parent
                    text: "App Drawer (QML)"
                    color: "white"
                    font.pixelSize: 48
                }
            }
        }
        
        // Page 1: Clock / Home
        Item {
            id: homePage
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: backend ? backend.currentTime : "12:00"
                    color: "white"
                    font.pixelSize: 120
                    font.bold: true
                }
            }
        }
        
        // Page 2: Settings
        Item {
            id: settingsPage
            Rectangle {
                anchors.fill: parent
                color: "#181825"
                Text {
                    anchors.centerIn: parent
                    text: "Settings (QML)"
                    color: "white"
                    font.pixelSize: 48
                }
            }
        }
    }

    // Page indicator
    PageIndicator {
        id: indicator
        count: swipeView.count
        currentIndex: swipeView.currentIndex
        anchors.bottom: swipeView.bottom
        anchors.bottomMargin: 40
        anchors.horizontalCenter: parent.horizontalCenter
    }

    // Control Center (Hardware Accelerated Blur)
    Item {
        id: controlCenter
        anchors.fill: parent
        visible: ccOpacity > 0
        
        property real ccOpacity: 0.0
        
        // Dim overlay
        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: controlCenter.ccOpacity * 0.4
        }
        
        // Glassmorphic Panel
        Rectangle {
            id: ccPanel
            width: parent.width * 0.4
            height: parent.height * 0.8
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 20
            anchors.rightMargin: 20
            radius: 40
            color: Qt.rgba(0.2, 0.2, 0.2, 0.5)
            opacity: controlCenter.ccOpacity
            
            // This is the Qt6 hardware blur effect
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 64
                blur: 1.0 // 100% of blurMax
                saturation: 0.2
            }
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                
                Text {
                    text: "Control Center"
                    color: "white"
                    font.pixelSize: 48
                    font.bold: true
                }
                
                // Brightness Slider
                Slider {
                    Layout.fillWidth: true
                    value: 0.8
                }
                
                Item { Layout.fillHeight: true }
            }
            
            // Slide animation
            transform: Translate {
                y: -ccPanel.height * (1.0 - controlCenter.ccOpacity)
            }
        }
        
        // Mouse area for swiping down from top right
    }
    
    // Invisible drag handle for Control Center
    MouseArea {
        id: ccDragHandle
        anchors.top: parent.top
        anchors.right: parent.right
        width: parent.width / 2
        height: 100
        
        property real startY: 0
        property bool isDragging: false
        
        onPressed: (mouse) => {
            startY = mouse.y
            isDragging = true
        }
        
        onPositionChanged: (mouse) => {
            if (isDragging) {
                let dy = mouse.y - startY
                let progress = Math.max(0, Math.min(1, dy / (parent.height * 0.4)))
                controlCenter.ccOpacity = progress
            }
        }
        
        onReleased: {
            isDragging = false
            if (controlCenter.ccOpacity > 0.3) {
                // Snap open
                ccAnim.to = 1.0
                ccAnim.start()
            } else {
                // Snap closed
                ccAnim.to = 0.0
                ccAnim.start()
            }
        }
    }
    
    // Animation for snapping
    NumberAnimation {
        id: ccAnim
        target: controlCenter
        property: "ccOpacity"
        duration: 300
        easing.type: Easing.OutCubic
    }
}
