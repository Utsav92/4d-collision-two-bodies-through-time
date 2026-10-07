// ===== TEMPORAL MESH skin lines: contour rings + longitudinal ribbons =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    int vid = gl_VertexID;
    int inst = TDInstanceID();
    int fi = sliceSample(inst);
    int stp = max(int(U(1).y + 0.5), 1);
    int lo = max(0, int(floor(U(0).x)) - int(U(1).x + 0.5) + 1);
    if (fi < 0 || U(18).y < 0.01) { kill(); return; }
    int bear = vid / 512;
    if ((bear == 0 && U(9).x < 0.5) || (bear == 1 && U(9).y < 0.5)) { kill(); return; }
    int rem = vid % 512;
    int seg = rem / 2;
    int ev = rem & 1;
    int base = bear * NPB + NIN;
    PB p0, p1;
    if (seg < NCON) {
        p0 = placeBody(base + seg, fi, true);
        p1 = placeBody(base + (seg + 1) % NCON, fi, true);
    } else {
        int c = seg - NCON;
        int fj = fi - stp;
        if (fj < lo) { kill(); return; }
        p0 = placeBody(base + c, fi, true);
        p1 = placeBody(base + c, fj, true);
        if (p0.a0.w < 0.5 || p1.a0.w < 0.5 || distance(p0.p, p1.p) > float(stp) * U(0).w + 2.6) { kill(); return; }
    }
    if (p0.a0.w < 0.5 || p1.a0.w < 0.5) { kill(); return; }
    PB v = ev == 0 ? p0 : p1;
    float lum = dot(v.a1.rgb, vec3(0.299, 0.587, 0.114));
    vec3 col = bodyColor(v, bear, lum) * 1.1;
    float fade = mix(1.0, exp(-v.age * 2.5), U(7).z);
    float alpha = 0.60 * U(19).w * U(18).y * fade * (seg < NCON ? 0.8 : 1.0) * clamp(float(stp) / 3.0, 0.22, 1.6);
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;
    alpha *= 1.0 + 0.9 * (distBoost() - 1.0);
    vec4 cp = uTDMats[TDCameraIndex()].camProj * vec4(v.p, 1.0);
    if (cp.w <= 0.05) { kill(); return; }
    gl_Position = cp;
    vCol = vec4(col, alpha);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
