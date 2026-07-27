import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Item {
    id: root
    property string activeClock: ""
    property var settings: backend ? JSON.parse(backend.clockSettingsJson || "{}") : {}
    property var clockConfig: settings[activeClock] || {}
    
    signal close()
    
    Rectangle {
        anchors.fill: parent
        color: "#E60C0C0E" // Semi-transparent black
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 40
            spacing: 20
            
            Text {
                text: "Customize " + root.activeClock
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            
            // Analog Clock gets Black/White theme
            RowLayout {
                visible: root.activeClock === "AnalogClock"
                Layout.alignment: Qt.AlignHCenter
                spacing: 40
                
                Button {
                    text: "Dark Theme"
                    onClicked: if (backend) backend.setClockSetting("AnalogClock", "theme", "dark")
                }
                Button {
                    text: "Light Theme"
                    onClicked: if (backend) backend.setClockSetting("AnalogClock", "theme", "light")
                }
            }
            
            // Other clocks get Solid/Gradient/Photo
            TabBar {
                id: tabs
                visible: root.activeClock !== "AnalogClock"
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                TabButton { text: "Solid Colors" }
                TabButton { text: "Gradients" }
                TabButton { text: "Photo" }
            }
            
            StackLayout {
                visible: root.activeClock !== "AnalogClock"
                currentIndex: tabs.currentIndex
                Layout.fillWidth: true
                Layout.fillHeight: true
                
                // Solid Colors
                Item {
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 20
                        Repeater {
                            model: ["#FFFFFF", "#E24A4A", "#5A8DEF", "#7B61FF", "#4AE28A", "#F2C94C"]
                            Rectangle {
                                width: 80; height: 80; radius: 40
                                color: modelData
                                border.width: clockConfig["bgValue"] === modelData ? 4 : 0
                                border.color: "white"
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
                        spacing: 20
                        Repeater {
                            model: [
                                ["#ff9966", "#ff5e62"],
                                ["#56ab2f", "#a8e063"],
                                ["#4568dc", "#b06ab3"]
                            ]
                            Rectangle {
                                width: 80; height: 80; radius: 40
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: modelData[0] }
                                    GradientStop { position: 1.0; color: modelData[1] }
                                }
                                border.width: clockConfig["bgValue"] === modelData[0] ? 4 : 0
                                border.color: "white"
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
                        Button {
                            text: "Select Photo from Gallery"
                            onClicked: galleryPicker.visible = true
                        }
                    }
                }
            }
            
            Button {
                Layout.alignment: Qt.AlignHCenter
                text: "Done"
                onClicked: root.close()
            }
        }
    }
    
    // Simple Gallery Picker Overlay
    Rectangle {
        id: galleryPicker
        anchors.fill: parent
        color: "#121215"
        visible: false
        z: 10
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            
            Text {
                text: "Choose a Photo"
                color: "white"
                font.pixelSize: 24
                Layout.alignment: Qt.AlignHCenter
            }
            
            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 150
                cellHeight: 150
                model: ["gallery/1.jpg", "gallery/2.jpg", "gallery/3.jpg"] // MOCK
                delegate: Image {
                    width: 140; height: 140
                    source: modelData
                    fillMode: Image.PreserveAspectCrop
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            cropperOverlay.sourceImage = modelData
                            cropperOverlay.visible = true
                            galleryPicker.visible = false
                        }
                    }
                }
            }
            
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignHCenter
                onClicked: galleryPicker.visible = false
            }
        }
    }
    
    // Simple Cropper Overlay
    Rectangle {
        id: cropperOverlay
        anchors.fill: parent
        color: "black"
        visible: false
        z: 20
        
        property string sourceImage: ""
        
        Flickable {
            anchors.fill: parent
            contentWidth: img.width * img.scale
            contentHeight: img.height * img.scale
            boundsBehavior: Flickable.StopAtBounds
            
            PinchArea {
                width: Math.max(parent.width, img.width * img.scale)
                height: Math.max(parent.height, img.height * img.scale)
                
                property real initialWidth
                property real initialHeight
                
                onPinchStarted: {
                    initialWidth = img.width * img.scale
                    initialHeight = img.height * img.scale
                }
                
                onPinchUpdated: (pinch) => {
                    img.scale += pinch.scale - pinch.previousScale
                    img.scale = Math.max(0.1, Math.min(img.scale, 5.0))
                }
                
                Image {
                    id: img
                    source: cropperOverlay.sourceImage
                    anchors.centerIn: parent
                    fillMode: Image.PreserveAspectFit
                }
            }
        }
        
        RowLayout {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 40
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 40
            
            Button {
                text: "Cancel"
                onClicked: cropperOverlay.visible = false
            }
            Button {
                text: "Apply"
                onClicked: {
                    cropperOverlay.visible = false
                    if (backend) {
                        backend.setClockSetting(root.activeClock, "bgType", "photo")
                        backend.setClockSetting(root.activeClock, "bgValue", cropperOverlay.sourceImage)
                        // Note: A true image crop would save a new file here using QImage in python.
                        // For Kiosk OS, applying the photo and letting QML scale it is sufficient.
                    }
                }
            }
        }
    }
}
