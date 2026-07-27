import QtQuick
import QtQuick.Layouts

Item {
    width: parent ? parent.width : 1024
    height: parent ? parent.height : 600

    property string timeStr: backend ? backend.currentTime : "12:00"
    property string hourStr: timeStr.split(":")[0] || "12"
    property string minStr: timeStr.split(":")[1] || "00"
    
    // Update date dynamically
    property string dateStr: ""
    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            dateStr = new Date().toLocaleDateString(Qt.locale("en_US"), "dddd, MMM d")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: -40

            Text {
                text: hourStr
                color: "white"
                font.family: "Google Sans"
                font.weight: Font.Bold
                font.pixelSize: 280
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: minStr
                color: "#5A8DEF"
                font.family: "Google Sans"
                font.weight: Font.Bold
                font.pixelSize: 280
                Layout.alignment: Qt.AlignHCenter
            }

            Item { height: 20 }

            Text {
                text: dateStr
                color: "#AAAAAA"
                font.family: "Google Sans"
                font.pixelSize: 32
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
