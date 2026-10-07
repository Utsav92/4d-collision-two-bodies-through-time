// ===== PARTICLE DUST : bodies shed fine dust, strongest at collisions, dissolves and explosions =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;
void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    if (U(19).y < 0.001) { kill(); return; }
    int id = gl_VertexID;
    int inst = TDInstanceID();
    uint key = uint(id) * 7717u + uint(inst) * 104729u + 17u;
    float r0 = h01(key), r1 = h01(key + 1u), r2 = h01(key + 2u);
    int headI = int(floor(U(0).x));
    int lo = max(0, headI - int(U(1).x + 0.5) + 1);
    int fi = clamp(headI - int(pow(r0, 1.7) * float(headI - lo + 1)), lo, min(headI, int(U(9).z + 0.5)));
    int k = int(r1 * 1535.0);
    int bear = k / NPB;
    if ((bear == 0 && U(9).x < 0.5) || (bear == 1 && U(9).y < 0.5)) { kill(); return; }
    PB b = placeBody(k, fi, true);
    if (b.a0.w < 0.5) { kill(); return; }
    float clk = U(9).w;
    float life = fract(r2 + clk * 0.11);
    vec3 drift = vec3(b.a2.xy * 0.25, 0.0) + curl(b.p * 0.4 + clk * 0.2) * 0.9 + vec3(0.0, 0.22, 0.0);
    vec3 p = b.p + drift * life * 2.2 + gauss3(key + 3u) * 0.04;
    float weight = U(19).y * (0.10 + 1.3 * U(7).y + 1.1 * U(6).w + 1.2 * b.inter * b.inter);
    float alpha = weight * sin(PI * life) * 0.28 * (1.0 - 0.6 * b.age);
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;
    float lum = dot(b.a1.rgb, vec3(0.299, 0.587, 0.114));
    vec3 col = mix(vec3(0.75, 0.85, 1.0), bodyColor(b, bear, lum), 0.4) * 1.3;
    vec4 vpos = uTDMats[TDCameraIndex()].cam * vec4(p, 1.0);
    vec4 cpos = uTDMats[TDCameraIndex()].camProj * vec4(p, 1.0);
    if (cpos.w <= 0.05) { kill(); return; }
    gl_Position = cpos;
    float size = 0.0075 * distBoost() * U(2).x * (0.6 + 1.0 * life);
    gl_PointSize = clamp(size * U(11).w / max(-vpos.z, 0.05) * 2.0, 1.2, 24.0);
    vCol = vec4(col, alpha);
    vDirS = vec2(1, 0); vElong = 0.0; vSoft = 1.0;
}
