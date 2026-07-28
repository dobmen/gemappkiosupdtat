import QtQuick
import QtQuick.Controls
import QtQuick.Layouts


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
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#1A1A24" }
                    GradientStop { position: 1.0; color: "#0C0C0E" }
                }
                
                Loader {
                    id: clockLoader
                    anchors.fill: parent
                    source: backend ? (backend.activeClockface + ".qml") : "ClassicClock.qml"
                }

                MouseArea {
                    anchors.fill: parent
                    onPressAndHold: {
                        clockSelectorAnim.to = 1.0
                        clockSelectorAnim.start()
                    }
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
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#1A1A24" }
                    GradientStop { position: 1.0; color: "#0C0C0E" }
                }
                
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
        interactive: controlCenter.ccOpacity < 0.01 && notifsPanel.nfOpacity < 0.01
        
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
                            color: tapKill.pressed ? "#E24A4A" : "#26E24A4A"
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
                    color: tapCloseAll.pressed ? "#E24A4A" : "#19E24A4A"
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
                    
                    color: (!modelData.icon) ? fallbackColor : (tapArea.pressed ? "#26FFFFFF" : "transparent")
                    
                    Text {
                        anchors.centerIn: parent
                        text: modelData.name.charAt(0).toUpperCase()
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 50
                        visible: !modelData.icon
                    }
                    
                    Canvas {
                        id: iconCanvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.reset();
                            ctx.beginPath();
                            ctx.arc(width/2, height/2, width/2, 0, 2 * Math.PI);
                            ctx.clip();
                            ctx.drawImage(modelData.icon, 0, 0, width, height);
                        }
                        Component.onCompleted: loadImage(modelData.icon)
                        onImageLoaded: requestPaint()
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
                        if (backend) {
                            let pt = iconCanvas.mapToItem(null, 0, 0) // root/global coords
                            backend.launchAppFromIcon(modelData.name, pt.x, pt.y, iconCanvas.width, iconCanvas.height)
                        }
                    }
                }
            }
        }
    }


    // ==========================================
    // 3. CONTROL CENTER (Sliding Panel from Top Right)
    // ==========================================
    
    // --- TRANSLUCENT OVERLAY FALLBACK ---
    property real overlayOpacity: Math.max(controlCenter.ccOpacity, notifsPanel.nfOpacity)
    
    Rectangle {
        anchors.fill: parent
        color: "#E6111118"
        opacity: overlayOpacity
        visible: overlayOpacity > 0
        z: 1
    }
    
    Item {
        id: controlCenter
        anchors.fill: parent
        visible: ccOpacity > 0
        z: 2
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
            height: Math.min(parent.height * 0.9, 850)
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 20
            anchors.rightMargin: 20
            radius: 40
            color: "transparent"
            opacity: controlCenter.ccOpacity
            
            Rectangle {
                anchors.fill: parent
                radius: 40
                color: "#E6111118"
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
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: 30
                        color: (backend && backend.dndEnabled) ? "#7B61FF" : "#19FFFFFF"
                        Text {
                            anchors.centerIn: parent
                            text: "🌙 DND"
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 20
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.toggleDND()
                        }
                    }
                    
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: 30
                        color: (backend && backend.silentEnabled) ? "#E24A4A" : "#19FFFFFF"
                        Text {
                            anchors.centerIn: parent
                            text: "🔕 Silent"
                            color: "white"
                            font.family: boldFont.name
                            font.pixelSize: 20
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.toggleSilent()
                        }
                    }
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    height: 180
                    radius: 30
                    color: "#0CFFFFFF"
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 30
                        spacing: 20
                        
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 15
                            Text { text: "☀️"; font.pixelSize: 24; color: "white" }
                            Slider {
                                Layout.fillWidth: true
                                from: 0; to: 100
                                value: backend ? backend.brightness : 80
                                onValueChanged: if (backend) backend.brightness = value
                                background: Rectangle {
                                    x: parent.leftPadding
                                    y: parent.topPadding + parent.availableHeight / 2 - height / 2
                                    width: parent.availableWidth; height: 40
                                    radius: 20; color: "#33FFFFFF"
                                    Rectangle { width: parent.visualPosition * parent.width; height: parent.height; color: "white"; radius: 20 }
                                }
                                handle: Item {}
                            }
                        }
                        
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 15
                            Text { text: "🔊"; font.pixelSize: 24; color: "white" }
                            Slider {
                                Layout.fillWidth: true
                                from: 0; to: 100
                                value: backend ? backend.volume : 50
                                onValueChanged: if (backend) backend.volume = value
                                background: Rectangle {
                                    x: parent.leftPadding
                                    y: parent.topPadding + parent.availableHeight / 2 - height / 2
                                    width: parent.availableWidth; height: 40
                                    radius: 20; color: "#33FFFFFF"
                                    Rectangle { width: parent.visualPosition * parent.width; height: parent.height; color: "white"; radius: 20 }
                                }
                                handle: Item {}
                            }
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
    
    // ==========================================
    // 4. NOTIFICATION CENTER (Left Sliding Panel)
    // ==========================================
    Item {
        id: notifsPanel
        anchors.fill: parent
        visible: nfOpacity > 0
        z: 2
        property real nfOpacity: 0.0
        
        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: notifsPanel.nfOpacity * 0.4
            MouseArea {
                anchors.fill: parent
                onClicked: { nfAnim.to = 0.0; nfAnim.start() }
                
                property real startY: 0
                onPressed: (mouse) => { startY = mouse.y }
                onPositionChanged: (mouse) => {
                    let dy = mouse.y - startY
                    if (dy < 0) {
                        notifsPanel.nfOpacity = 1.0 + (dy / nfContainer.height)
                    }
                }
                onReleased: (mouse) => {
                    if (notifsPanel.nfOpacity < 0.8) {
                        nfAnim.to = 0.0; nfAnim.start()
                    } else {
                        nfAnim.to = 1.0; nfAnim.start()
                    }
                }
            }
        }
        
        Item {
            id: nfContainer
            width: parent.width * 0.45
            height: Math.min(parent.height * 0.9, 850)
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.topMargin: 20
            anchors.leftMargin: 20
            visible: notifsPanel.nfOpacity > 0
            
            Rectangle {
                anchors.fill: parent
                radius: 40
                color: "#E6111118"
                border.color: "#19FFFFFF"
                border.width: 1
                opacity: notifsPanel.nfOpacity
            }
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 40
                spacing: 20
                
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Recent Alerts"
                        color: "white"
                        font.family: boldFont.name
                        font.pixelSize: 32
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        width: 120; height: 50
                        radius: 25; color: "#26FFFFFF"
                        Text { anchors.centerIn: parent; text: "Clear All"; color: "white"; font.pixelSize: 18; font.family: boldFont.name }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: if (backend) backend.clearNotifications()
                        }
                    }
                }
                
                ListView {
                    id: notifList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 15
                    model: backend ? backend.notifications : []
                    
                    delegate: Rectangle {
                        width: notifList.width
                        height: 90
                        radius: 20
                        color: "#22222B"
                        border.color: "#2F2F3B"
                        border.width: 1
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 15
                            
                            Rectangle {
                                width: 50; height: 50; radius: 25; color: "#19FFFFFF"
                                Text { anchors.centerIn: parent; text: modelData.icon; font.pixelSize: 24 }
                            }
                            
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: modelData.title; color: "white"; font.family: boldFont.name; font.pixelSize: 18 }
                                Text { text: modelData.desc; color: "#AAAAAA"; font.family: mainFont.name; font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                            
                            Rectangle {
                                width: 40; height: 40; radius: 20; color: "transparent"
                                Text { anchors.centerIn: parent; text: "✕"; color: "#888888"; font.pixelSize: 20; font.family: boldFont.name }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: if (backend) backend.removeNotification(index)
                                }
                            }
                        }
                    }
                }
            }
            
            transform: Translate {
                id: nfTranslate
                y: -nfContainer.height * (1.0 - notifsPanel.nfOpacity)
            }
        }
    }
    
    // Top left invisible swipe handle for Notification Center
    MouseArea {
        id: nfDragHandle
        x: 0; y: 0
        width: parent.width / 2
        height: 150
        
        property real startY: 0
        property real startOpacity: 0
        property bool isDragging: false
        
        onPressed: (mouse) => {
            startY = mouse.y
            startOpacity = notifsPanel.nfOpacity
            isDragging = true
        }
        
        onPositionChanged: (mouse) => {
            if (isDragging) {
                let dy = mouse.y - startY
                if (dy > 0) {
                    let newOpacity = startOpacity + (dy / nfContainer.height)
                    notifsPanel.nfOpacity = Math.max(0, Math.min(1, newOpacity))
                }
            }
        }
        
        onReleased: {
            isDragging = false
            if (notifsPanel.nfOpacity > 0.3) {
                nfAnim.to = 1.0; nfAnim.start()
            } else {
                nfAnim.to = 0.0; nfAnim.start()
            }
        }
    }
    
    NumberAnimation {
        id: nfAnim
        target: notifsPanel
        property: "nfOpacity"
        duration: 350
        easing.type: Easing.OutCubic
    }

    // ==========================================
    // 5. TOAST NOTIFICATION OVERLAY
    // ==========================================
    Rectangle {
        id: toastPopup
        width: 420
        height: 85
        anchors.horizontalCenter: parent.horizontalCenter
        y: -120
        radius: 42
        color: "#22222B"
        border.color: "#33333F"
        border.width: 1
        z: 900
        
        property string tApp: ""
        property string tTitle: ""
        property string tDesc: ""
        property string tIcon: "🔔"
        
        RowLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 15
            
            Rectangle {
                width: 50; height: 50; radius: 25; color: "#19FFFFFF"
                Text { anchors.centerIn: parent; text: toastPopup.tIcon; font.pixelSize: 24 }
            }
            
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: toastPopup.tTitle; color: "white"; font.family: boldFont.name; font.pixelSize: 18 }
                Text { text: toastPopup.tDesc; color: "#AAAAAA"; font.family: mainFont.name; font.pixelSize: 16 }
            }
        }
        
        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (toastPopup.tApp && backend) backend.launch_app(toastPopup.tApp)
                toastAnimOut.start()
            }
        }
        
        NumberAnimation {
            id: toastAnimIn
            target: toastPopup
            property: "y"
            to: 25
            duration: 450
            easing.type: Easing.OutBack
            onFinished: toastTimer.start()
        }
        
        NumberAnimation {
            id: toastAnimOut
            target: toastPopup
            property: "y"
            to: -120
            duration: 400
            easing.type: Easing.InBack
        }
        
        Timer {
            id: toastTimer
            interval: 4000
            onTriggered: toastAnimOut.start()
        }
    }
    
    // ==========================================
    // 6. VOICE ASSISTANT OVERLAY
    // ==========================================
    Rectangle {
        id: voiceOverlay
        anchors.fill: parent
        color: "#CC000000"
        z: 950
        opacity: 0.0
        visible: opacity > 0
        
        property string vText: "Listening..."
        
        Behavior on opacity { NumberAnimation { duration: 250 } }
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 30
            
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "🎙️"
                font.pixelSize: 100
                color: "white"
            }
            
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: voiceOverlay.vText
                color: "white"
                font.family: boldFont.name
                font.pixelSize: 48
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.maximumWidth: root.width * 0.8
            }
        }
    }
    
    // ==========================================
    // SYSTEM APP TRANSITION OVERLAY
    // ==========================================
    Rectangle {
        id: appTransitionOverlay
        anchors.fill: parent
        color: "black"
        opacity: 0.0
        z: 999
        visible: opacity > 0
        
        Behavior on opacity {
            NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
        }
    }
    
    // ==========================================
    // 7. CLOCK SELECTOR OVERLAY
    // ==========================================
    Rectangle {
        id: clockSelector
        anchors.fill: parent
        color: "#1A1A24"
        z: 980
        visible: opacity > 0
        opacity: 0.0

        property var faces: ["ClassicClock", "StackedClock", "AnalogClock"]
        property bool showCustomizer: false

        ColumnLayout {
            id: clockSelectorLayout
            anchors.fill: parent
            spacing: 20
            visible: !clockSelector.showCustomizer

            Text {
                text: "Swipe to browse • Tap to apply"
                color: "#AAAAAA"
                font.family: boldFont.name
                font.pixelSize: 24
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 40
            }

            ListView {
                id: clockListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: ListView.Horizontal
                snapMode: ListView.SnapOneItem
                highlightRangeMode: ListView.StrictlyEnforceRange
                model: clockSelector.faces
                spacing: 40
                
                scale: 1.0 + (1.0 - clockSelector.opacity) * 0.25
                opacity: clockSelector.opacity
                
                delegate: Item {
                    width: clockListView.width
                    height: clockListView.height
                    
                        // The preview container (80% of list view)
                        Item {
                            anchors.centerIn: parent
                            width: parent.width * 0.8
                            height: parent.height * 0.8
                            
                            // The actual clock loaded at full screen size and visually scaled down!
                            Loader {
                                anchors.centerIn: parent
                                width: root.width
                                height: root.height
                                scale: parent.width / root.width
                                source: modelData + ".qml"
                                onLoaded: {
                                    if (item.hasOwnProperty("previewRadius")) {
                                        item.previewRadius = 30 / (parent.width / root.width)
                                    }
                                }
                            }
                            
                            // A border overlay for the preview bounds
                            Rectangle {
                                anchors.fill: parent
                                color: "transparent"
                                border.color: "#333340"
                                border.width: 2
                                radius: 30
                                z: 10
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (backend) backend.activeClockface = modelData
                                    clockSelectorAnim.to = 0.0
                                    clockSelectorAnim.start()
                                }
                            }
                        }
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: 60
                spacing: 30
                
                Rectangle {
                    width: 160
                    height: 60
                    radius: 30
                    color: "#2C2C35"
                    Text { anchors.centerIn: parent; text: "Cancel"; color: "white"; font.family: boldFont.name; font.pixelSize: 20 }
                    MouseArea { 
                        anchors.fill: parent
                        onClicked: {
                            clockSelectorAnim.to = 0.0
                            clockSelectorAnim.start()
                        }
                    }
                }
                
                Rectangle {
                    width: 160
                    height: 60
                    radius: 30
                    color: "#5A8DEF"
                    Text { anchors.centerIn: parent; text: "Customize"; color: "white"; font.family: boldFont.name; font.pixelSize: 20 }
                    MouseArea { 
                        anchors.fill: parent
                        onClicked: clockSelector.showCustomizer = true 
                    }
                }
            }
        }
        
        Loader {
            anchors.fill: parent
            visible: clockSelector.showCustomizer
            active: clockSelector.showCustomizer
            source: "ClockCustomizer.qml"
            onLoaded: {
                item.activeClock = clockSelector.faces[clockListView.currentIndex]
                item.close.connect(function() {
                    clockSelector.showCustomizer = false
                })
            }
        }

        NumberAnimation {
            id: clockSelectorAnim
            target: clockSelector
            property: "opacity"
            duration: 300
            easing.type: Easing.OutCubic
            onFinished: if (clockSelectorAnim.to === 0.0) clockSelector.showCustomizer = false
        }
    }

    // ==========================================
    // 8. BOOT VIDEO PLAYER
    // ==========================================
    Loader {
        id: bootVideoLoader
        anchors.fill: parent
        z: 1000
        active: false
        source: "BootVideoPlayer.qml"
        onLoaded: {
            if (item && item.play) {
                item.play()
            }
        }
    }

    Connections {
        target: backend
        function onAppOpened(appName) {
            appTransitionOverlay.opacity = 1.0
        }
        function onAppMinimized() {
            appTransitionOverlay.opacity = 0.0
        }
        function onShowToast(app, title, desc, icon) {
            toastPopup.tApp = app
            toastPopup.tTitle = title
            toastPopup.tDesc = desc
            toastPopup.tIcon = icon
            toastAnimOut.stop()
            toastTimer.stop()
            toastAnimIn.start()
        }
        function onVoiceListening() {
            voiceOverlay.vText = "Listening..."
            voiceOverlay.opacity = 1.0
        }
        function onVoiceUpdate(text) {
            voiceOverlay.vText = text
        }
        function onVoiceHide() {
            voiceOverlay.opacity = 0.0
        }
        function onPlayBootVideo() {
            bootVideoLoader.active = true
        }
    }
}
