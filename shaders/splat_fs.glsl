// ===== soft elliptical splat footprint (Gaussian-like), aligned to projected velocity =====
in vec4 vCol;
in vec2 vDirS;
in float vElong;
in float vSoft;
layout(location = 0) out vec4 fragColor;

void main() {
    vec2 q = (gl_PointCoord - 0.5) * 2.0;
    q.y = -q.y;
    vec2 d = normalize(vDirS);
    float a = dot(q, d);
    float b = dot(q, vec2(-d.y, d.x));
    float minor = 1.0 / (1.0 + vElong);
    float e = a * a + (b * b) / (minor * minor);
    if (e > 1.0) discard;
    float g = exp(-3.4 * e);                      // Gaussian falloff
    float disk = smoothstep(1.0, 0.7, e);         // crisp point
    float w = mix(disk, g, vSoft);
    fragColor = TDOutputSwizzle(vec4(vCol.rgb * vCol.a * w, w * vCol.a));
}
