// ===== TEMPORAL SHOCKWAVES : every strong collision leaves expanding rings that stay as historical markers =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
const int RSEG = 96;
void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    int vid = gl_VertexID;
    int inst = TDInstanceID();
    int e = inst / 3, rp = inst % 3;
    vec4 evt = texelFetch(sEv, ivec2(e, 0), 0);
    if (evt.w <= 0.0 || U(16).w < 0.5) { kill(); return; }
    float head = U(0).x;
    if (evt.x > head + 0.5) { kill(); return; }
    float tau = max(head - evt.x, 0.0) / 12.5;
    int seg = vid / 2, ev = vid & 1;
    float ang = 6.2831853 * float(seg + ev) / float(RSEG);
    float grow = 1.0 - exp(-tau * 1.1 * U(16).y);
    float R = (0.15 + U(16).y * 2.4 * grow) * (1.0 - 0.22 * float(rp)) * (0.6 + 0.8 * evt.w);
    R *= 1.0 + 0.18 * (vnoise(vec3(cos(ang) * 2.0, sin(ang) * 2.0, float(e) * 3.1 + float(rp))) - 0.5);
    vec2 cc = toDisplayUp(evt.yz);
    vec3 p = vec3(cc + R * vec2(cos(ang), sin(ang)), 0.0);
    float s = (evt.x - U(0).y) * U(0).w;
    p = timePath(p, s);
    float a = evt.w * (0.10 + 0.90 * exp(-tau * 0.9)) * (1.0 - 0.25 * float(rp));
    if (evt.x > U(0).z + 0.5) a *= U(3).z;
    vec3 col = mix(vec3(0.5, 0.85, 1.0), vec3(1.0, 0.9, 0.75), exp(-tau * 2.0)) * 1.6;
    vec4 cp = uTDMats[TDCameraIndex()].camProj * vec4(p, 1.0);
    if (cp.w <= 0.05) { kill(); return; }
    gl_Position = cp;
    vCol = vec4(col, a * 0.9);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
