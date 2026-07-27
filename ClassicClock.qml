import QtQuick
import QtQuick.Layouts

Item {
    width: parent ? parent.width : 1024
    height: parent ? parent.height : 600

    property string timeStr: backend ? backend.currentTime : "12:00"
    
    // Update date dynamically
    property string dateStr: ""
    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            dateStr = new Date().toLocaleDateString(Qt.locale("en_US"), "dddd, MMMM d")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 10

            Text {
                text: timeStr
                color: "white"
                font.family: "Google Sans"
                font.weight: Font.Bold
                font.pixelSize: 220
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: dateStr
                color: "white"
                font.family: "Google Sans"
                font.pixelSize: 32
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
