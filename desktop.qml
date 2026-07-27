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

    // ==========================================
    // 1. BACKGROUND PAGES (Horizontal Swipe)
    // ==========================================
    SwipeView {
        id: swipeView
        anchors.fill: parent
        orientation: Qt.Horizontal
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

        // Page 1: Media
        Item {
            id: mediaPage
            Rectangle {
                anchors.fill: parent
                color: "#0C0C0E"
                
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

    // ==========================================
    // 2. APP DRAWER (Native QML Drawer)
    // ==========================================
    Drawer {
        id: appDrawer
        width: parent.width
        height: parent.height
        edge: Qt.BottomEdge
        dragMargin: 150 // Allow starting swipe from bottom 150px
        
        background: Rectangle {
            color: "#121215"
        }
        
        // Header Row for Drawer
        RowLayout {
            id: drawerHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 40
            height: 60
            
            Rectangle {
                id: activeTasksBtn
                height: 50
                width: 250
                color: "transparent"
                radius: 10
                border.color: tapBtn.pressed ? "#333333" : "transparent"
                
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 15
                    Text {
                        text: "🗂️ Active Tasks"
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 26
                    }
                    Rectangle {
                        visible: backend && backend.activeTasks.length > 0
                        width: 40
                        height: 40
                        radius: 20
                        color: "#E24A4A"
                        Text {
                            anchors.centerIn: parent
                            text: backend ? backend.activeTasks.length : "0"
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 20
                        }
                    }
                }
                MouseArea {
                    id: tapBtn
                    anchors.fill: parent
                    onClicked: taskRibbon.visible = !taskRibbon.visible
                }
            }
            
            Item { Layout.fillWidth: true } // Spacer
            
            Text {
                text: "▼ Pull down to close"
                color: "#555555"
                font.family: boldFont.name
                font.pixelSize: 24
            }
            
            Item { width: 250 } // Right spacer to balance center
        }

        // Active Tasks Ribbon
        Rectangle {
            id: taskRibbon
            anchors.top: drawerHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 20
            height: 140
            color: "#1A1A22"
            visible: false
            border.color: "#2A2A35"
            border.width: 1
            
            ListView {
                anchors.fill: parent
                anchors.margins: 20
                orientation: ListView.Horizontal
                spacing: 20
                model: backend ? backend.activeTasks : []
                clip: true
                
                delegate: Rectangle {
                    width: 320
                    height: 100
                    radius: 12
                    color: "#24242E"
                    border.color: "#333340"
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 20
                        
                        Image {
                            source: modelData.icon
                            Layout.preferredWidth: 50
                            Layout.preferredHeight: 50
                            fillMode: Image.PreserveAspectFit
                        }
                        
                        Text {
                            text: modelData.name
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 24
                            Layout.fillWidth: true
                            
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (backend) backend.launch_app(modelData.name)
                                    appDrawer.close()
                                }
                            }
                        }
                        
                        Rectangle {
                            Layout.preferredWidth: 60
                            Layout.preferredHeight: 60
                            radius: 30
                            color: tapKill.pressed ? "#E24A4A" : "rgba(226,74,74,0.15)"
                            Text {
                                anchors.centerIn: parent
                                text: "✕"
                                color: tapKill.pressed ? "white" : "#E24A4A"
                                font.family: boldFont.name
                                font.pixelSize: 24
                            }
                            MouseArea {
                                id: tapKill
                                anchors.fill: parent
                                onClicked: if (backend) backend.kill_app(modelData.name)
                            }
                        }
                    }
                }
                
                footer: Rectangle {
                    width: 200
                    height: 100
                    radius: 12
                    color: tapCloseAll.pressed ? "#E24A4A" : "rgba(226,74,74,0.1)"
                    border.color: "#E24A4A"
                    border.width: 1
                    visible: backend && backend.activeTasks.length > 1
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Close All"
                        color: tapCloseAll.pressed ? "white" : "#E24A4A"
                        font.family: boldFont.name
                        font.pixelSize: 24
                    }
                    
                    MouseArea {
                        id: tapCloseAll
                        anchors.fill: parent
                        onClicked: if (backend) backend.kill_all_apps()
                    }
                }
            }
        }
        
        GridView {
            id: appGrid
            anchors.top: taskRibbon.visible ? taskRibbon.bottom : drawerHeader.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 40
            anchors.topMargin: 60
            cellWidth: width / 4
            cellHeight: 250
            model: backend ? backend.apps : []
            clip: true
            
            // Close the drawer if pulled down past the top!
            onMovementEnded: {
                if (atYBeginning && contentY < -150) {
                    appDrawer.close()
                }
            }
            
            delegate: Item {
                width: appGrid.cellWidth
                height: appGrid.cellHeight
                
                Rectangle {
                    id: appBg
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 20
                    width: 130
                    height: 130
                    radius: 65 
                    
                    property var colors: ["#E24A4A", "#5A8DEF", "#F39C12", "#27AE60", "#8E44AD", "#9B59B6"]
                    property string fallbackColor: colors[modelData.name.length % colors.length]
                    
                    color: (appIcon.status === Image.Error || appIcon.status === Image.Null) ? fallbackColor : (tapArea.pressed ? "rgba(255,255,255,0.15)" : "transparent")
                    
                    Text {
                        anchors.centerIn: parent
                        text: modelData.name.charAt(0).toUpperCase()
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 50
                        visible: (appIcon.status === Image.Error || appIcon.status === Image.Null)
                    }
                    
                    // Mask source for MultiEffect
                    Rectangle {
                        id: maskRect
                        anchors.fill: parent
                        radius: 65
                        visible: false
                    }
                    
                    ShaderEffectSource {
                        id: maskSource
                        sourceItem: maskRect
                        visible: false
                    }
                    
                    Image {
                        id: appIcon
                        anchors.fill: parent
                        source: modelData.icon
                        fillMode: Image.PreserveAspectCrop
                        visible: false
                    }
                    
                    // True GPU circular clipping mask for square icons!
                    MultiEffect {
                        source: appIcon
                        anchors.fill: parent
                        maskEnabled: true
                        maskSource: maskSource
                        visible: (appIcon.status === Image.Ready)
                    }
                }
                
                Text {
                    anchors.top: appBg.bottom
                    anchors.topMargin: 15
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: modelData.name
                    color: "white"
                    font.family: boldFont.name
                    font.pixelSize: 32
                    font.weight: Font.Bold
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


    // ==========================================
    // 3. CONTROL CENTER (Sliding Panel from Top Right)
    // ==========================================
    Item {
        id: controlCenter
        anchors.fill: parent
        visible: ccOpacity > 0
        property real ccOpacity: 0.0
        
        // Dim overlay when CC is open
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
                
                // Allow swipe UP anywhere on the screen when CC is open to close it!
                property real startY: 0
                onPressed: (mouse) => { startY = mouse.y }
                onPositionChanged: (mouse) => {
                    let dy = mouse.y - startY
                    if (dy < 0) {
                        controlCenter.ccOpacity = 1.0 + (dy / ccPanel.height)
                    }
                }
                onReleased: (mouse) => {
                    if (controlCenter.ccOpacity < 0.8) {
                        ccAnim.to = 0.0
                        ccAnim.start()
                    } else {
                        ccAnim.to = 1.0
                        ccAnim.start()
                    }
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
                sourceRect: Qt.rect(ccPanel.x, ccPanel.y - ccTranslate.y, ccPanel.width, ccPanel.height)
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
                border.color: "#19FFFFFF"
                border.width: 1
            }
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 30
                
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
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    
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
                
                Item { Layout.fillHeight: true }
            }
            
            transform: Translate {
                id: ccTranslate
                y: -ccPanel.height * (1.0 - controlCenter.ccOpacity)
            }
        }
    }
    
    // Top right invisible swipe handle for Control Center
    MouseArea {
        id: ccDragHandle
        x: parent.width / 2
        width: parent.width / 2
        height: 150
        y: 0
        
        property real startY: 0
        property real startOpacity: 0
        property bool isDragging: false
        
        onPressed: (mouse) => {
            startY = mouse.y
            startOpacity = controlCenter.ccOpacity
            isDragging = true
        }
        
        onPositionChanged: (mouse) => {
            if (isDragging) {
                let dy = mouse.y - startY
                if (dy > 0) {
                    let newOpacity = startOpacity + (dy / ccPanel.height)
                    controlCenter.ccOpacity = Math.max(0, Math.min(1, newOpacity))
                }
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
