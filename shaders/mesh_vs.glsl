// ===== TEMPORAL MESH : faces between the contour of slice t and slice t-step, for both bears =====
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
    int fj = fi - stp;
    int lo = max(0, int(floor(U(0).x)) - int(U(1).x + 0.5) + 1);
    if (fi < 0 || fj < lo || U(18).y < 0.01) { kill(); return; }
    int bear = vid / 768;
    if ((bear == 0 && U(9).x < 0.5) || (bear == 1 && U(9).y < 0.5)) { kill(); return; }
    int q = (vid % 768) / 6;
    int tv = vid % 6;
    int c0 = q, c1 = (q + 1) % NCON;
    int cs, fr;
    if (tv == 0)      { cs = c0; fr = fi; }
    else if (tv == 1) { cs = c1; fr = fi; }
    else if (tv == 2) { cs = c0; fr = fj; }
    else if (tv == 3) { cs = c1; fr = fi; }
    else if (tv == 4) { cs = c1; fr = fj; }
    else              { cs = c0; fr = fj; }
    int base = bear * NPB + NIN;
    PB v = placeBody(base + cs, fr, true);
    PB w = placeBody(base + cs, fr == fi ? fj : fi, true);
    if (v.a0.w < 0.5 || w.a0.w < 0.5) { kill(); return; }
    float lim = float(stp) * U(0).w + 2.6;
    if (distance(v.p, w.p) > lim) { kill(); return; }
    float lum = dot(v.a1.rgb, vec3(0.299, 0.587, 0.114));
    vec3 col = bodyColor(v, bear, lum);
    float fade = mix(1.0, exp(-v.age * 2.5), U(7).z);
    float alpha = 0.07 * U(19).w * U(18).y * fade * clamp(float(stp) / 3.0, 0.22, 1.6);
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;
    vec4 cp = uTDMats[TDCameraIndex()].camProj * vec4(v.p, 1.0);
    if (cp.w <= 0.05) { kill(); return; }
    gl_Position = cp;
    vCol = vec4(col, alpha);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
