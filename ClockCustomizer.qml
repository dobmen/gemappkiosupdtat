import QtQuick
import QtQuick.Layouts
import QtQuick.Controls


Item {
    id: root
    property string activeClock: ""
    property var settings: backend ? JSON.parse(backend.clockSettingsJson || "{}") : {}
    property var clockConfig: settings[activeClock] || {}
    
    signal close()
    
    // Smooth fade in
    opacity: 0
    Component.onCompleted: opacity = 1.0
    Behavior on opacity { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
    
    Rectangle {
        anchors.fill: parent
        color: "#99000000" // Dim background
        
        MouseArea { anchors.fill: parent; onClicked: root.close() }
        
        // One UI Style Card at the bottom
        Rectangle {
            width: parent.width
            height: Math.min(parent.height * 0.9, 700)
            anchors.bottom: parent.bottom
            color: "#18181A"
            radius: 40
            
            // Prevent clicks from falling through
            MouseArea { anchors.fill: parent }
            
            ScrollView {
                anchors.fill: parent
                anchors.margins: 20
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 30
                    
                    Text {
                        text: "Customize " + root.activeClock
                        color: "white"
                        font.pixelSize: 32
                        font.bold: true
                        font.family: "Google Sans"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 20
                    }
                    
                    // Analog Clock gets Black/White theme
                    RowLayout {
                        visible: root.activeClock === "AnalogClock"
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 40
                        
                        Rectangle {
                            width: 150; height: 60; radius: 30
                            color: clockConfig.theme === "dark" || !clockConfig.theme ? "#333333" : "#222222"
                            Text { anchors.centerIn: parent; text: "Dark Theme"; color: "white"; font.family: "Google Sans"; font.pixelSize: 18 }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: if (backend) backend.setClockSetting("AnalogClock", "theme", "dark")
                            }
                        }
                        Rectangle {
                            width: 150; height: 60; radius: 30
                            color: clockConfig.theme === "light" ? "#333333" : "#222222"
                            Text { anchors.centerIn: parent; text: "Light Theme"; color: "white"; font.family: "Google Sans"; font.pixelSize: 18 }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: if (backend) backend.setClockSetting("AnalogClock", "theme", "light")
                            }
                        }
                    }
                    
                    // Segmented Control (One UI style) for Solid/Gradient/Photo
                    Item {
                        id: segmentedControl
                        visible: root.activeClock !== "AnalogClock"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
                        
                        property int currentIndex: 0
                        
                        Rectangle {
                            anchors.fill: parent
                            color: "#222222"
                            radius: 30
                        }
                        
                        RowLayout {
                            anchors.fill: parent
                            spacing: 0
                            
                            Repeater {
                                model: ["Solid", "Gradient", "Photo"]
                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    
                                    Rectangle {
                                        anchors.fill: parent
                                        anchors.margins: 5
                                        radius: 25
                                        color: segmentedControl.currentIndex === index ? "#444444" : "transparent"
                                        Behavior on color { ColorAnimation { duration: 200 } }
                                    }
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData
                                        color: segmentedControl.currentIndex === index ? "white" : "#AAAAAA"
                                        font.family: "Google Sans"
                                        font.pixelSize: 18
                                        font.bold: segmentedControl.currentIndex === index
                                    }
                                    
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: segmentedControl.currentIndex = index
                                    }
                                }
                            }
                        }
                    }
                    
                    StackLayout {
                        visible: root.activeClock !== "AnalogClock"
                        currentIndex: segmentedControl.currentIndex
                        Layout.fillWidth: true
                        Layout.preferredHeight: 200
                        
                        // Solid Colors
                        Item {
                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 30
                                Repeater {
                                    model: ["transparent", "#000000", "#FFFFFF", "#E24A4A", "#5A8DEF", "#7B61FF", "#4AE28A", "#F2C94C"]
                                    Rectangle {
                                        width: 80; height: 80; radius: 40
                                        color: modelData
                                        border.width: (clockConfig["bgValue"] === modelData || (clockConfig["bgValue"] === undefined && modelData === "transparent")) ? 5 : 2
                                        border.color: modelData === "transparent" ? "#888888" : (clockConfig["bgValue"] === modelData ? "white" : "#444444")
                                        
                                        // Checkerboard pattern for transparent option
                                        Rectangle {
                                            anchors.centerIn: parent
                                            width: 40; height: 40
                                            color: "transparent"
                                            visible: modelData === "transparent"
                                            Text { anchors.centerIn: parent; text: "∅"; color: "#888888"; font.pixelSize: 30 }
                                        }
                                        
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: if (backend) {
                                                backend.setClockSetting(root.activeClock, "bgType", "solid")
                                                backend.setClockSetting(root.activeClock, "bgValue", modelData)
                                            }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Gradients
                    Item {
                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 30
                            Repeater {
                                model: [
                                    ["#ff9966", "#ff5e62"],
                                    ["#56ab2f", "#a8e063"],
                                    ["#4568dc", "#b06ab3"],
                                    ["#232526", "#414345"]
                                ]
                                Rectangle {
                                    width: 80; height: 80; radius: 40
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: modelData[0] }
                                        GradientStop { position: 1.0; color: modelData[1] }
                                    }
                                    border.width: clockConfig["bgValue"] === modelData[0] ? 5 : 0
                                    border.color: "#888888"
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: if (backend) {
                                            backend.setClockSetting(root.activeClock, "bgType", "gradient")
                                            backend.setClockSetting(root.activeClock, "bgValue", modelData[0])
                                            backend.setClockSetting(root.activeClock, "bgValue2", modelData[1])
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Photo
                    Item {
                        ColumnLayout {
                            anchors.centerIn: parent
                            Rectangle {
                                width: 300; height: 80; radius: 40
                                color: "#333333"
                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 15
                                    Text { text: "🖼️"; font.pixelSize: 24 }
                                    Text {
                                        text: "Select Photo"
                                        color: "white"
                                        font.family: "Google Sans"
                                        font.pixelSize: 20
                                    }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: galleryPicker.visible = true
                                }
                            }
                        }
                    }
                }
                
                // Done Button
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 200
                    height: 60
                    radius: 30
                    color: "#5A8DEF"
                    
                    Text {
                        anchors.centerIn: parent
                        text: "Done"
                        color: "white"
                        font.family: "Google Sans"
                        font.pixelSize: 20
                        font.bold: true
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            root.opacity = 0.0
                            hideTimer.start()
                        }
                    }
                }
                }
            }
        }
    }
    Timer {
        id: hideTimer
        interval: 300
        onTriggered: root.close()
    }
    
    // Gallery Picker Overlay
    Rectangle {
        id: galleryPicker
        anchors.fill: parent
        color: "#121215"
        visible: false
        z: 10
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 40
            spacing: 20
            
            Text {
                text: "Gallery"
                color: "white"
                font.family: "Google Sans"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            
            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 200
                cellHeight: 200
                model: ["gallery/1.jpg", "gallery/2.jpg", "gallery/3.jpg"]
                delegate: Rectangle {
                    width: 180; height: 180
                    color: "transparent"
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        clip: true
                        radius: 20
                        
                        Image {
                            id: galleryImg
                            anchors.fill: parent
                            source: "file:///" + backend.getAppPath() + "/" + modelData
                            fillMode: Image.PreserveAspectCrop
                        }
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (backend) {
                                backend.setClockSetting(root.activeClock, "bgType", "photo")
                                backend.setClockSetting(root.activeClock, "bgValue", backend.getAppPath() + "/" + modelData)
                            }
                            galleryPicker.visible = false
                        }
                    }
                }
            }
            
            Rectangle {
                width: 200; height: 60; radius: 30
                color: "#333333"
                Layout.alignment: Qt.AlignHCenter
                Text { anchors.centerIn: parent; text: "Cancel"; color: "white"; font.family: "Google Sans"; font.pixelSize: 20 }
                MouseArea { anchors.fill: parent; onClicked: galleryPicker.visible = false }
            }
        }
    }
}
