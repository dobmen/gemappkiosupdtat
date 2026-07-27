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

    property var settings: backend ? JSON.parse(backend.clockSettingsJson || "{}") : {}
    property var clockConfig: settings["ClassicClock"] || {}
    property string bgType: clockConfig.bgType ? clockConfig.bgType : "solid"
    property string bgValue: clockConfig.bgValue ? clockConfig.bgValue : (backend ? backend.clockAccentColor : "#3498db")
    property string bgValue2: clockConfig.bgValue2 ? clockConfig.bgValue2 : "#000000"

    Rectangle {
        anchors.fill: parent
        color: bgType === "solid" ? bgValue : "black"
        
        Rectangle {
            anchors.fill: parent
            visible: bgType === "gradient"
            gradient: Gradient {
                GradientStop { position: 0.0; color: bgType === "gradient" ? bgValue : "transparent" }
                GradientStop { position: 1.0; color: bgType === "gradient" ? bgValue2 : "transparent" }
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
            spacing: 10
            
            Text {
                text: timeStr
                color: backend ? backend.clockAccentColor : "white"
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
