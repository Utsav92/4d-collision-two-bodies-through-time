// ===== slice frames: bounding rectangles of each bear per time slice (TIME SLICES mode) =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    int vid = gl_VertexID;
    int inst = TDInstanceID();
    int fi = sliceSample(inst);
    int mode = int(U(4).x + 0.5);
    if (fi < 0 || (mode != 3 && U(21).y < 0.5)) { kill(); return; }
    if (mode == 3) {
        int sp = max(int(U(10).x + 0.5), 1);
        if (((int(floor(U(0).x)) - fi) % sp) != 0) { kill(); return; }
    }
    int bear = vid / 8;
    if ((bear == 0 && U(9).x < 0.5) || (bear == 1 && U(9).y < 0.5)) { kill(); return; }
    int e = (vid % 8) / 2;
    int ev = vid & 1;
    vec4 bb = texelFetch(sInfo, ivec2(4 + bear, fi), 0);
    if (bb.z - bb.x < 0.01) { kill(); return; }
    vec2 c[5] = vec2[5](bb.xy, vec2(bb.z, bb.y), bb.zw, vec2(bb.x, bb.w), bb.xy);
    vec2 pu = c[e + ev];
    vec2 d = toDisplayUp(pu);
    vec3 p = vec3(d, 0.0);
    p.x += (bear == 0 ? -0.5 : 0.5) * U(3).w;
    float s = (float(fi) - U(0).y) * U(0).w;
    p = timePath(p, s);
    float age = clamp((U(0).x - float(fi)) / max(U(1).x - 1.0, 1.0), 0.0, 1.0);
    vec3 col = bear == 0 ? U(13).rgb : U(14).rgb;
    float alpha = 0.55 * max(U(10).z, 0.4) * exp(-age * 1.2);
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;
    alpha *= 1.0 + 0.9 * (distBoost() - 1.0);
    vec4 cp = uTDMats[TDCameraIndex()].camProj * vec4(p, 1.0);
    if (cp.w <= 0.05) { kill(); return; }
    gl_Position = cp;
    vCol = vec4(col * 1.4, alpha);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
