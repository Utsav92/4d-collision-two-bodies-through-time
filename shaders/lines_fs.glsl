in vec4 vCol;
in vec2 vDirS;
in float vElong;
in float vSoft;
layout(location = 0) out vec4 fragColor;
void main() {
    fragColor = TDOutputSwizzle(vec4(vCol.rgb * vCol.a, vCol.a));
}
