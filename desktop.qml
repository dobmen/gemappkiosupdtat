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
    
    color: "#0C0C0E"
    
    FontLoader { id: mainFont; source: "fonts/GoogleSans-Regular.ttf" }
    FontLoader { id: boldFont; source: "fonts/GoogleSans-Bold.ttf" }

    SwipeView {
        id: swipeView
        anchors.fill: parent
        currentIndex: 1 
        
        // Page 0: App Drawer
        Item {
            id: appDrawerPage
            Rectangle {
                anchors.fill: parent
                color: "#121215"
                
                GridView {
                    id: appGrid
                    anchors.fill: parent
                    anchors.margins: 60
                    anchors.topMargin: 100
                    cellWidth: parent.width / 4
                    cellHeight: cellWidth * 1.2
                    model: backend ? backend.apps : []
                    clip: true
                    
                    delegate: Item {
                        width: appGrid.cellWidth
                        height: appGrid.cellHeight
                        
                        Rectangle {
                            id: appBg
                            anchors.centerIn: parent
                            width: parent.width * 0.8
                            height: parent.width * 0.8
                            color: tapArea.pressed ? "rgba(255,255,255,0.1)" : "transparent"
                            radius: 30
                            
                            Image {
                                anchors.centerIn: parent
                                width: parent.width * 0.6
                                height: parent.width * 0.6
                                source: modelData.icon
                                fillMode: Image.PreserveAspectFit
                            }
                        }
                        
                        Text {
                            anchors.top: appBg.bottom
                            anchors.topMargin: 15
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.name
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 18
                        }
                        
                        MouseArea {
                            id: tapArea
                            anchors.fill: parent
                            onClicked: {
                                if (backend) backend.launch_app(modelData.name)
                            }
                        }
                    }
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
                    font.family: boldFont.name
                    font.pixelSize: 220
                }
                
                Text {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 80
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "▲ Swipe right for apps"
                    color: "#555555"
                    font.family: boldFont.name
                    font.pixelSize: 24
                }
            }
        }
        
        // Page 2: Media
        Item {
            id: mediaPage
            Rectangle {
                anchors.fill: parent
                color: "#181825"
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 20
                    
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Now Playing"
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 48
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "No active stream • Swipe up to launch Spotify"
                        color: "#AAAAAA"
                        font.family: mainFont.name
                        font.pixelSize: 24
                    }
                }
            }
        }
    }

    PageIndicator {
        id: indicator
        count: swipeView.count
        currentIndex: swipeView.currentIndex
        anchors.bottom: swipeView.bottom
        anchors.bottomMargin: 40
        anchors.horizontalCenter: parent.horizontalCenter
    }

    // Hardware Accelerated Control Center
    Item {
        id: controlCenter
        anchors.fill: parent
        visible: ccOpacity > 0
        property real ccOpacity: 0.0
        
        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: controlCenter.ccOpacity * 0.4
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    ccAnim.to = 0.0
                    ccAnim.start()
                }
            }
        }
        
        Rectangle {
            id: ccPanel
            width: parent.width * 0.45
            height: parent.height * 0.65
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 20
            anchors.rightMargin: 20
            radius: 40
            color: Qt.rgba(0.1, 0.1, 0.1, 0.6)
            opacity: controlCenter.ccOpacity
            
            // True GPU Hardware Blur
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 80
                blur: 1.0 
                saturation: 0.2
            }
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 30
                
                // Header
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Control Center"
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 32
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        width: 50
                        height: 50
                        radius: 25
                        color: "rgba(255, 50, 50, 0.8)"
                        Text {
                            anchors.centerIn: parent
                            text: "⏻"
                            color: "white"
                            font.pixelSize: 24
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.shutdown()
                        }
                    }
                }
                
                // Connection Toggles
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    
                    // Network
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: 30
                        color: (backend && backend.networkEnabled) ? "#5A8DEF" : "rgba(255,255,255,0.1)"
                        Text {
                            anchors.centerIn: parent
                            text: "📶 Network"
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 20
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.toggleNetwork()
                        }
                    }
                    
                    // Bluetooth
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: 30
                        color: (backend && backend.bluetoothEnabled) ? "#5A8DEF" : "rgba(255,255,255,0.1)"
                        Text {
                            anchors.centerIn: parent
                            text: "󰂯 Bluetooth"
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 20
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.toggleBluetooth()
                        }
                    }
                }
                
                // Sliders
                Item { Layout.fillHeight: true }
            }
            
            transform: Translate {
                y: -ccPanel.height * (1.0 - controlCenter.ccOpacity)
            }
        }
    }
    
    // Top right invisible swipe handle
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
                ccAnim.to = 1.0
                ccAnim.start()
            } else {
                ccAnim.to = 0.0
                ccAnim.start()
            }
        }
    }
    
    NumberAnimation {
        id: ccAnim
        target: controlCenter
        property: "ccOpacity"
        duration: 350
        easing.type: Easing.OutCubic
    }
}
