// ===== CONTACT FIELD : organic fibres bridging Bear A and Bear B, one set per time slice (they persist = contact memory) =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
const int SEG = 10;
void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    int vid = gl_VertexID;
    int kf = vid / (2 * SEG);
    int sg = (vid / 2) % SEG;
    int ev = vid & 1;
    int inst = TDInstanceID();
    int fi = sliceSample(inst);
    if (fi < 0 || U(19).x < 0.001 || U(16).z < 0.5) { kill(); return; }
    int mode = int(U(4).x + 0.5);
    if (mode == 3) {
        int sp = max(int(U(10).x + 0.5), 1);
        int rel = int(floor(U(0).x)) - fi;
        if ((rel % sp) != 0) { kill(); return; }
    }
    vec4 pr = texelFetch(sPairs, ivec2(kf, fi), 0);
    if (pr.w < 0.5 || pr.z > U(15).x) { kill(); return; }
    uint key = uint(kf) * 6151u + uint(fi) * 90001u;
    if (h01(key) > U(15).z) { kill(); return; }
    if (U(9).x < 0.5 || U(9).y < 0.5) { kill(); return; }
    int kA = int(pr.x + 0.5), kB = NPB + int(pr.y + 0.5);
    PB a = placeBody(kA, fi, true);
    PB b = placeBody(kB, fi, true);
    if (a.a0.w < 0.5 || b.a0.w < 0.5) { kill(); return; }
    float u = float(sg + ev) / float(SEG);
    vec3 base = mix(a.p, b.p, u);
    vec3 dir = b.p - a.p;
    float L = length(dir) + 1e-4;
    vec3 dn = dir / L;
    vec3 n1 = normalize(cross(dn, vec3(0.0, 0.0, 1.0)) + vec3(1e-3, 0.0, 0.0));
    vec3 n2 = cross(n1, dn);
    float bulge = sin(PI * u);
    float wob = U(15).w;
    vec3 off = (n1 * (h01(key + 1u) - 0.5) + vec3(0.0, 0.0, 1.0) * (h01(key + 2u) - 0.5) * 2.2 + n2 * (h01(key + 3u) - 0.5)) * bulge * wob * (0.15 + L * 0.8);
    off += vnoise3(base * 1.7 + vec3(u * 3.0, float(kf) * 0.37, U(9).w * 0.5)) * bulge * wob * 0.5;
    base += off;
    float age = a.age;
    float fade = mix(exp(-age * 4.0), 1.0, U(15).y);
    float close = 1.0 - clamp(pr.z / max(U(15).x, 1e-3), 0.0, 1.0);
    float inter = 0.5 * (a.inter + b.inter);
    float alpha = 0.34 * clamp(float(max(int(U(1).y + 0.5), 1)) / 3.0, 0.25, 1.6) * U(16).x * U(19).x * fade * (0.30 + 0.70 * close) * (0.35 + 1.0 * inter);
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;
    alpha *= 1.0 + 0.9 * (distBoost() - 1.0);
    vec3 col = mix(U(13).rgb, U(14).rgb, u) * 1.25 + vec3(1.0, 0.9, 0.8) * close * close * 0.12;
    vec4 cp = uTDMats[TDCameraIndex()].camProj * vec4(base, 1.0);
    if (cp.w <= 0.05) { kill(); return; }
    gl_Position = cp;
    vCol = vec4(col, alpha);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
