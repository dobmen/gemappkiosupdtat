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

    property var settings: backend ? JSON.parse(backend.clockSettingsJson || "{}") : {}
    property var clockConfig: settings["StackedClock"] || {}
    property string bgType: clockConfig.bgType ? clockConfig.bgType : "solid"
    property string bgValue: clockConfig.bgValue ? clockConfig.bgValue : (backend ? backend.clockAccentColor : "#FF2A55")
    property string bgValue2: clockConfig.bgValue2 ? clockConfig.bgValue2 : "#000000"

    Rectangle {
        anchors.fill: parent
        color: bgType === "solid" ? bgValue : "black"
        
        Rectangle {
            anchors.fill: parent
            visible: bgType === "gradient"
            gradient: Gradient {
                GradientStop { position: 0.0; color: (bgType === "gradient" ? bgValue : "transparent") }
                GradientStop { position: 1.0; color: (bgType === "gradient" ? bgValue2 : "transparent") }
            }
        }
        
        Image {
            anchors.fill: parent
            source: bgType === "photo" ? "file:///" + bgValue : ""
            visible: bgType === "photo"
            fillMode: Image.PreserveAspectCrop
        }

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
                color: backend ? backend.clockAccentColor : "#5A8DEF"
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
