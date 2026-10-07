// ===== NOW plane (scan plane) and the video plane: unit grid mesh scaled to the footage frame =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
out vec2 vUV2;
uniform vec4 uPlane;   // x: 0 = scan plane, 1 = video plane ; y = opacity
void main() {
    vec2 xy = P.xy;                              // grid SOP spans -0.5..0.5
    bool video = uPlane.x > 0.5;
    float sPlane = video ? (U(21).z - U(0).y) * U(0).w - 0.03 : (U(0).z - U(0).y) * U(0).w;
    vec3 p = vec3(xy.x * 11.5 * (video ? 1.0 : 1.12), xy.y * 6.469 * (video ? 1.0 : 1.12), 0.0);
    p = timePath(p, sPlane);
    gl_Position = uTDMats[TDCameraIndex()].camProj * vec4(p, 1.0);
    vUV2 = xy + 0.5;
    vCol = vec4(1.0);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
