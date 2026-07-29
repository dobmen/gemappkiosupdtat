cmake_minimum_required(VERSION 3.16)
project(kiosk_os VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTORCC ON)

# Find Qt modules
find_package(Qt6 REQUIRED COMPONENTS 
    Core 
    Gui 
    Qml 
    Quick 
    WaylandCompositor
    ShaderTools
)

qt_add_executable(kiosk_os
    main.cpp
    resources.qrc
)

qt6_add_shaders(kiosk_os "shaders"
    PREFIX "/"
    FILES blur.frag
)

target_link_libraries(kiosk_os PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::WaylandCompositor
    Qt6::ShaderTools
)

# Enable QML resource compilation
set_target_properties(kiosk_os PROPERTIES
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)
