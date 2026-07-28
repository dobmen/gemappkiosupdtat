import QtQuick

Item {
    id: analogRoot
    width: parent ? parent.width : 1024
    height: parent ? parent.height : 600

    property real hours: new Date().getHours()
    property real minutes: new Date().getMinutes()
    property real seconds: new Date().getSeconds()
    
    property var settings: backend ? JSON.parse(backend.clockSettingsJson || "{}") : {}
    property var clockConfig: settings["AnalogClock"] || {}
    property string theme: clockConfig.theme ? clockConfig.theme : "dark"
    property color bg: theme === "dark" ? "#121215" : "#EEEEEE"
    property color fg: theme === "dark" ? "white" : "black"
    property color accent: backend ? backend.clockAccentColor : "#3498db"

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            let d = new Date();
            analogRoot.hours = d.getHours()
            analogRoot.minutes = d.getMinutes()
            analogRoot.seconds = d.getSeconds()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: analogRoot.bg

        Item {
            anchors.centerIn: parent
            width: 400
            height: 400

            // Ring
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.color: fg
                border.width: 10
            }

            // Ticks
            Repeater {
                model: 12
                Rectangle {
                    width: 6
                    height: 25
                    color: fg
                    x: parent.width / 2 - width / 2
                    y: 10
                    transformOrigin: Item.Bottom
                    transform: Rotation {
                        origin.x: 3
                        origin.y: 190
                        angle: index * 30
                    }
                }
            }

            // Hour Hand
            Rectangle {
                width: 12
                height: 110
                color: fg
                radius: 6
                x: parent.width / 2 - width / 2
                y: parent.height / 2 - height + 10
                transformOrigin: Item.Bottom
                rotation: (analogRoot.hours % 12) * 30 + (analogRoot.minutes / 60) * 30
                Behavior on rotation { NumberAnimation { duration: 200 } }
            }

            // Minute Hand
            Rectangle {
                width: 8
                height: 160
                color: accent
                radius: 4
                x: parent.width / 2 - width / 2
                y: parent.height / 2 - height + 10
                transformOrigin: Item.Bottom
                rotation: analogRoot.minutes * 6 + (analogRoot.seconds / 60) * 6
                Behavior on rotation { NumberAnimation { duration: 200 } }
            }

            // Second Hand
            Rectangle {
                width: 4
                height: 180
                color: backend ? backend.clockAccentColor : "#E24A4A"
                radius: 2
                x: parent.width / 2 - width / 2
                y: parent.height / 2 - height + 30
                transformOrigin: Item.Bottom
                rotation: analogRoot.seconds * 6
                Behavior on rotation { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
            }
            
            // Center Dot
            Rectangle {
                width: 24
                height: 24
                radius: 12
                color: fg
                anchors.centerIn: parent
            }
        }
    }
}
