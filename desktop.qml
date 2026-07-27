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
    visibility: Window.FullScreen
    flags: Qt.FramelessWindowHint
    
    color: "#0C0C0E"
    
    FontLoader { id: mainFont; source: "fonts/GoogleSans-Regular.ttf" }
    FontLoader { id: boldFont; source: "fonts/GoogleSans-Bold.ttf" }

    SwipeView {
        id: swipeView
        anchors.fill: parent
        orientation: Qt.Vertical
        currentIndex: 0 
        
        // Page 0: Clock / Home
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
                    text: "▲ Swipe up for apps"
                    color: "#555555"
                    font.family: boldFont.name
                    font.pixelSize: 24
                }
            }
        }

        // Page 1: App Drawer
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
                            color: tapArea.pressed ? "#19FFFFFF" : "transparent"
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
            color: "transparent"
            opacity: controlCenter.ccOpacity
            
            ShaderEffectSource {
                id: effectSource
                sourceItem: swipeView
                sourceRect: Qt.rect(ccPanel.x, ccPanel.y - ccPanel.transform[0].y, ccPanel.width, ccPanel.height)
                visible: false
            }
            
            MultiEffect {
                source: effectSource
                anchors.fill: parent
                blurEnabled: true
                blurMax: 80
                blur: 1.0 
                saturation: 0.2
            }
            
            Rectangle {
                anchors.fill: parent
                radius: 40
                color: Qt.rgba(0.1, 0.1, 0.1, 0.5)
                border.color: "rgba(255,255,255,0.1)"
                border.width: 1
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
                        color: "#CCFF3232"
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
                        color: (backend && backend.networkEnabled) ? "#5A8DEF" : "#19FFFFFF"
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
                        color: (backend && backend.bluetoothEnabled) ? "#5A8DEF" : "#19FFFFFF"
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
                let progress = Math.max(0, Math.min(1, dy / ccPanel.height))
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
