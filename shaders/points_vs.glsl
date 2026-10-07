// ===== POINT CLOUD / GAUSSIAN-STYLE SPLATS, instanced per time slice =====
out vec4 vCol;
out vec2 vDirS;
out float vElong;
out float vSoft;

void kill() { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; vCol = vec4(0.0); vDirS = vec2(1, 0); vElong = 0.0; vSoft = 0.0; }

void main() {
    int k = gl_VertexID;
    int inst = TDInstanceID();
    vec4 u0 = U(0), u1 = U(1);
    int stp = max(int(u1.y + 0.5), 1);
    int headI = int(floor(u0.x));
    int fi = headI - inst * stp;
    int lo = max(0, headI - int(u1.x + 0.5) + 1);
    if (fi < lo || fi > int(U(9).z + 0.5)) { kill(); return; }
    int bear = k / NPB;
    int kk = k - bear * NPB;
    if ((bear == 0 && U(9).x < 0.5) || (bear == 1 && U(9).y < 0.5)) { kill(); return; }
    int mode = int(U(4).x + 0.5);
    int rel = headI - fi;
    if (mode == 3) {                                   // TIME SLICES
        int sp = max(int(U(10).x + 0.5), 1);
        if ((rel % sp) != 0 || rel / sp >= int(U(10).w + 0.5)) { kill(); return; }
    }
    int stride = max(int(u1.z + 0.5), 1);
    if ((kk % stride) != 0) { kill(); return; }
    uint key = uint(k) * 7919u + uint(fi) * 104729u;
    float rnd = h01(key);
    if (rnd > u1.w) { kill(); return; }

    PB b = placeBody(k, fi, true);
    if (b.a0.w < 0.5) { kill(); return; }
    float age = b.age;
    if (rnd < smoothstep(0.25, 1.0, age) * U(7).w * 0.97) { kill(); return; }   // TEMPORAL_DECAY: old history thins out

    float I = b.inter;
    vec3 p = b.p;
    float lum = dot(b.a1.rgb, vec3(0.299, 0.587, 0.114));
    float speed = b.a1.a;

    // ---- slit scan: only a moving vertical slab of every slice survives ----
    float wSlit = U(18).w;
    if (mode == 4) {
        // slit scan: the same screen column of EVERY slice (each slice in its own frame), laid out through time
        vec4 cm = texelFetch(sInfo, ivec2(7, fi), 0);
        vec2 q = b.a0.xy - cm.zw;
        float sc2 = max(cm.x * cm.x + cm.y * cm.y, 1e-6);
        vec2 own = vec2(cm.x * q.x + cm.y * q.y, -cm.y * q.x + cm.x * q.y) / sc2;
        if (abs(own.x - U(11).x) > U(11).y) { kill(); return; }
    }

    // ---- dissolve: old bodies turn to dust, contact fibres are untouched ----
    float dis = clamp((U(7).y * 1.25 - (1.0 - age)) * 3.0, 0.0, 1.0);
    // ---- explosion ----
    float ex = U(6).w;
    vec3 gdir = normalize(gauss3(key + 5u) + vec3(0.0, 0.0, 0.25));
    if (ex > 0.001) p += gdir * ex * U(7).x * (0.25 + h01(key + 9u) * 0.75) * (0.4 + age);
    if (dis > 0.0) p += (curl(p * 0.5 + U(9).w * 0.2) * 1.4 + gdir * 0.5) * dis * (0.5 + h01(key + 11u));

    // ---- size ----
    float size = 0.0105 * U(2).x * (1.0 + U(8).z * age * 1.2) * (1.0 + I * 0.7);
    float planeD = abs(float(fi) - U(0).z);
    float onPlane = smoothstep(1.6, 0.0, planeD) * U(11).z;
    size *= (1.0 + onPlane * 0.9);
    if (mode == 3) size *= U(10).y;
    size *= mix(1.0, 0.45, dis);
    float db = distBoost();
    size *= db;

    // ---- colour ----
    vec3 col = bodyColor(b, bear, lum);
    col = mix(col, vec3(1.0, 0.97, 0.9) * 1.8, onPlane * 0.7);
    col = mix(col, vec3(0.7, 0.8, 1.0), dis * 0.6);

    // ---- alpha ----
    float persist = max(U(8).x, 0.05);
    float ageO = mix(1.0, 1.0 - age * 0.85, U(8).y);
    float fadeT = mix(1.0, exp(-age * 3.0 / persist), U(7).z);
    float dens = clamp(float(stp) / 3.0, 0.22, 1.6);            // denser slice stacks must be dimmer or they saturate
    // when the time axis collapses (small TIME_DEPTH) many slices pile onto the same place: divide the pile-up out
    float depthTotal = U(0).w * U(9).z;
    float nSl = min(U(1).x, U(0).x + 1.0) / float(stp);
    float collapse = 1.0 - smoothstep(0.0, 16.0, depthTotal);
    dens /= (1.0 + collapse * nSl * 0.06);
    float alpha = 0.30 * U(2).y * ageO * fadeT * U(18).x * dens;
    if (mode == 3) alpha *= U(10).z * 1.6;
    if (mode == 4) alpha *= 1.8;
    if (float(fi) > U(0).z + 0.5) alpha *= U(3).z;                // future of the scan plane = ghost
    alpha *= mix(1.0, 0.12, dis);
    alpha *= (1.0 + I * 0.6) * (1.0 + 0.45 * (db - 1.0));

    vec4 vpos = uTDMats[TDCameraIndex()].cam * vec4(p, 1.0);
    vec4 cpos = uTDMats[TDCameraIndex()].camProj * vec4(p, 1.0);
    if (cpos.w <= 0.05) { kill(); return; }
    gl_Position = cpos;

    // ---- anisotropic splat: stretched along projected velocity ----
    vec3 vel = vec3(b.a2.xy, 0.0);
    float sp = length(vel);
    float elong = clamp(sp * U(2).w * 0.010 / max(size, 1e-3), 0.0, 6.0) * (1.0 - 0.7 * age);
    vec3 vd = sp > 1e-3 ? vel / sp : vec3(1, 0, 0);
    vec4 c2 = uTDMats[TDCameraIndex()].camProj * vec4(p + vd * 0.1, 1.0);
    vec2 sd = c2.xy / c2.w - cpos.xy / cpos.w;
    float asp = uTDMats[TDCameraIndex()].proj[1][1] / uTDMats[TDCameraIndex()].proj[0][0];
    sd.x *= 1.0 / max(asp, 1e-3);
    vDirS = length(sd) > 1e-6 ? normalize(sd) : vec2(1, 0);
    vElong = elong;
    float rpx = size * U(11).w / max(-vpos.z, 0.05);
    gl_PointSize = clamp(rpx * 2.0 * (1.0 + elong), 1.5, 80.0);
    vCol = vec4(col, alpha);
    vSoft = mix(0.0, 1.0, U(2).z) ;
}
