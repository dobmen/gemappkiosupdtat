#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(binding = 1) uniform sampler2D source;

// The UBO block required by Qt6 ShaderEffect
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 pixelSize; // Passed from QML for blur radius calculations
};

void main() {
    vec4 color = vec4(0.0);
    
    // A simple 9-tap custom GPU Gaussian Blur!
    // Bypassing broken Qt Wayland effects entirely.
    color += texture(source, qt_TexCoord0 + vec2(-pixelSize.x, -pixelSize.y)) * 0.0625;
    color += texture(source, qt_TexCoord0 + vec2(0.0, -pixelSize.y)) * 0.125;
    color += texture(source, qt_TexCoord0 + vec2(pixelSize.x, -pixelSize.y)) * 0.0625;
    
    color += texture(source, qt_TexCoord0 + vec2(-pixelSize.x, 0.0)) * 0.125;
    color += texture(source, qt_TexCoord0) * 0.25;
    color += texture(source, qt_TexCoord0 + vec2(pixelSize.x, 0.0)) * 0.125;
    
    color += texture(source, qt_TexCoord0 + vec2(-pixelSize.x, pixelSize.y)) * 0.0625;
    color += texture(source, qt_TexCoord0 + vec2(0.0, pixelSize.y)) * 0.125;
    color += texture(source, qt_TexCoord0 + vec2(pixelSize.x, pixelSize.y)) * 0.0625;
    
    // Tint slightly white for the frosted glass look
    color = mix(color, vec4(1.0, 1.0, 1.0, 1.0), 0.15);

    fragColor = color * qt_Opacity;
}
