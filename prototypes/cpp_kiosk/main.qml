import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

// Note: If Qt5Compat is throwing ABI errors on your VM, this will still fail in C++.
// import Qt5Compat.GraphicalEffects

Window {
    width: 1280
    height: 720
    visible: true
    title: qsTr("C++ Kiosk Prototype")
    color: "#000000"

    // Wallpaper
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#5A28FF" }
            GradientStop { position: 1.0; color: "#101018" }
        }
    }

    // Top Status Bar
    Item {
        id: statusBar
        width: parent.width
        height: 60
        anchors.top: parent.top

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            text: "🌤️ 72° Sunny"
            color: "white"
            font.pixelSize: 18
            font.bold: true
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            text: "🔔 3   📶  🔋 100%"
            color: "white"
            font.pixelSize: 18
            font.bold: true
        }

        // Click to toggle Control Center
        MouseArea {
            anchors.fill: parent
            onClicked: controlCenter.isOpen = !controlCenter.isOpen
        }
    }

    // Clock
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 10
        Text {
            text: "12:00"
            color: "white"
            font.pixelSize: 140
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Monday, January 1"
            color: "white"
            font.pixelSize: 28
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }

    // App Dock
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 40
        anchors.horizontalCenter: parent.horizontalCenter
        width: dockLayout.width + 60
        height: dockLayout.height + 40
        color: "#22ffffff" // Fallback semi-transparent since FastBlur breaks
        radius: 45
        border.color: "#33ffffff"

        RowLayout {
            id: dockLayout
            anchors.centerIn: parent
            spacing: 25

            Rectangle { width: 75; height: 75; radius: 20; color: "#1DB954"; Text { anchors.centerIn: parent; text: "🎵"; font.pixelSize: 36 } }
            Rectangle { width: 75; height: 75; radius: 20; color: "#FF0000"; Text { anchors.centerIn: parent; text: "▶️"; font.pixelSize: 36 } }
            Rectangle { width: 75; height: 75; radius: 20; color: "#2D9CDB"; Text { anchors.centerIn: parent; text: "🌤️"; font.pixelSize: 36 } }
        }
    }

    // Control Center Overlay
    Rectangle {
        id: controlCenter
        property bool isOpen: false
        
        width: parent.width * 0.8
        height: parent.height * 0.6
        anchors.horizontalCenter: parent.horizontalCenter
        
        // Animated transition
        y: isOpen ? 60 : -height - 50
        Behavior on y { NumberAnimation { duration: 400; easing.type: Easing.OutQuint } }

        color: "#AA14141C" // Fallback transparency without hardware blur
        radius: 40
        border.color: "#33ffffff"

        Text {
            anchors.top: parent.top
            anchors.topMargin: 40
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Control Center (No Blur)"
            color: "white"
            font.pixelSize: 28
            font.bold: true
        }
    }
}
