in vec4 vCol;
in vec2 vDirS;
in float vElong;
in float vSoft;
in vec2 vUV2;
uniform sampler2D sSrc;
uniform vec4 uPlane;
layout(location = 0) out vec4 fragColor;
void main() {
    if (uPlane.x > 0.5) {
        vec3 c = texture(sSrc, vUV2).rgb;
        fragColor = TDOutputSwizzle(vec4(c * uPlane.y, uPlane.y));
        return;
    }
    // scan plane: faint sheet + metric grid + glowing frame
    vec2 g = vUV2 * vec2(11.5 * 1.12, 6.469 * 1.12);
    vec2 f = abs(fract(g * 2.0) - 0.5);
    float grid = (1.0 - smoothstep(0.0, 0.035, min(f.x, f.y))) * 0.5;
    vec2 e = min(vUV2, 1.0 - vUV2);
    float edge = 1.0 - smoothstep(0.0, 0.012, min(e.x, e.y));
    float a = (0.035 + grid * 0.10 + edge * 0.6) * uPlane.y;
    vec3 col = vec3(0.55, 0.9, 1.0);
    fragColor = TDOutputSwizzle(vec4(col * a, a));
}
