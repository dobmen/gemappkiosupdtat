import QtQuick
import QtMultimedia

Rectangle {
    id: bootVideoOverlay
    color: "black"
    opacity: 0.0
    
    function play() {
        opacity = 1.0
        bootPlayer.play()
    }
    
    MediaPlayer {
        id: bootPlayer
        source: "file://" + Qt.application.dir + "/videos/update_boot.mp4"
        audioOutput: AudioOutput {}
        videoOutput: bootVideoOut
        
        onPlaybackStateChanged: {
            if (playbackState === MediaPlayer.StoppedState) {
                bootFadeOut.start()
            }
        }
        onErrorOccurred: {
            bootFadeOut.start()
        }
    }
    
    VideoOutput {
        id: bootVideoOut
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
    }
    
    NumberAnimation {
        id: bootFadeOut
        target: bootVideoOverlay
        property: "opacity"
        to: 0.0
        duration: 800
        easing.type: Easing.InOutQuad
        onFinished: {
            bootVideoOverlay.parent.active = false // Deactivate loader
        }
    }
}
