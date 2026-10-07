// ===== 4D COLLISION :: shared GLSL (prepended to every vertex pass) =====
// All parameters arrive in one float texture sU (width 32 x 1), written every frame by the runtime:
//  U0  (head, zref, plane, dz)                 newest sample index, sample that sits at z=0, scan-plane sample, world z per sample
//  U1  (histLen, sampleStep, pointStride, pointDensity)
//  U2  (pointSize, splatOpacity, gaussLook, motionStretch)
//  U3  (depthScale, depthContrast, ghost, bearSeparation)
//  U4  (tempMode, timeGeom, bend, twist)
//  U5  (bendRadius, collisionStrength, noiseAmount, noiseScale)
//  U6  (noiseSpeed, curl, turbulence, explode)
//  U7  (explodeForce, dissolve, temporalFade, temporalDecay)
//  U8  (pastPersistence, ageOpacity, agePointSize, colorMode)
//  U9  (showA, showB, lastSample, clock)
//  U10 (sliceSpacing, sliceThickness, sliceOpacity, sliceCount)
//  U11 (slitX, slitWidth, planeGlow, projScalePx)
//  U12 (camMap a, b, tcx, tcy)   present-frame camera mapping (stabilised -> present image)
//  U13 colour A   U14 colour B
//  U15 (contactThreshold, contactPersistence, contactDensity, contactWobble)
//  U16 (contactBright, shockSpeed, showContact, showShock)
//  U17 (bass, mid, high, transient)
//  U18 (wPoints, wMesh, wSlices, wSlit)
//  U19 (wContact, dustAmount, amplitude, meshOpacity)
//  U20 (camera position xyz, scanPlaneZ)
uniform sampler2D sU, sP0, sP1, sP2, sInfo, sPairs, sEv;

vec4 U(int i) { return texelFetch(sU, ivec2(i, 0), 0); }

const int NPB = 768;     // points per bear
const int NIN = 640;     // interior points per bear (contour points follow)
const int NCON = 128;
const float PI = 3.14159265;

uint pcg(uint v) {
    uint s = v * 747796405u + 2891336453u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float h01(uint v) { return float(pcg(v) & 0xFFFFFFu) / 16777216.0; }
vec3 h3(uint v) { return vec3(h01(v * 3u + 1u), h01(v * 3u + 2u), h01(v * 3u + 3u)); }
vec3 gauss3(uint k) {
    vec3 a = max(h3(k), vec3(1e-5)), b = h3(k + 0x9E3779B9u);
    return sqrt(-2.0 * log(a)) * cos(6.2831853 * b);
}

float vnoise(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n000 = h01(uint(int(i.x) * 73856093 ^ int(i.y) * 19349663 ^ int(i.z) * 83492791));
    float n100 = h01(uint(int(i.x + 1.0) * 73856093 ^ int(i.y) * 19349663 ^ int(i.z) * 83492791));
    float n010 = h01(uint(int(i.x) * 73856093 ^ int(i.y + 1.0) * 19349663 ^ int(i.z) * 83492791));
    float n110 = h01(uint(int(i.x + 1.0) * 73856093 ^ int(i.y + 1.0) * 19349663 ^ int(i.z) * 83492791));
    float n001 = h01(uint(int(i.x) * 73856093 ^ int(i.y) * 19349663 ^ int(i.z + 1.0) * 83492791));
    float n101 = h01(uint(int(i.x + 1.0) * 73856093 ^ int(i.y) * 19349663 ^ int(i.z + 1.0) * 83492791));
    float n011 = h01(uint(int(i.x) * 73856093 ^ int(i.y + 1.0) * 19349663 ^ int(i.z + 1.0) * 83492791));
    float n111 = h01(uint(int(i.x + 1.0) * 73856093 ^ int(i.y + 1.0) * 19349663 ^ int(i.z + 1.0) * 83492791));
    return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y), mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}
vec3 vnoise3(vec3 p) { return vec3(vnoise(p), vnoise(p + 31.7), vnoise(p + 77.3)) - 0.5; }
vec3 curl(vec3 p) {
    const float e = 0.35;
    vec3 dx = vnoise3(p + vec3(e, 0, 0)) - vnoise3(p - vec3(e, 0, 0));
    vec3 dy = vnoise3(p + vec3(0, e, 0)) - vnoise3(p - vec3(0, e, 0));
    vec3 dz = vnoise3(p + vec3(0, 0, e)) - vnoise3(p - vec3(0, 0, e));
    return vec3(dy.z - dz.y, dz.x - dx.z, dx.y - dy.x) / (2.0 * e);
}

// ---- stabilised world (centred, y down) -> present-frame display coords (y up) ----
vec2 toDisplay(vec2 p0) {
    vec4 m = U(12);
    vec2 q = p0 - m.zw;
    float s = max(m.x * m.x + m.y * m.y, 1e-6);
    vec2 d = vec2(m.x * q.x + m.y * q.y, -m.y * q.x + m.x * q.y) / s;
    return vec2(d.x, -d.y);
}
// same, for coordinates that are already y-up in the stabilised frame (info texture centroids / bboxes)
vec2 toDisplayUp(vec2 pUp) { return toDisplay(vec2(pUp.x, -pUp.y)); }

vec3 rotY(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z); }

// ---- the time axis. s = signed time distance in world units (past < 0). Returns warped position. ----
vec3 timePath(vec3 p, float s) {
    int mode = int(U(4).y + 0.5);
    float amt = U(4).z, tw = U(4).w, R = U(5).x;
    if (mode == 0 || amt < 1e-4) return p + vec3(0.0, 0.0, s);
    vec3 lin = p + vec3(0.0, 0.0, s);
    vec3 r = lin;
    if (mode == 1) {                         // CURVE : the time axis bends sideways like a road
        float th = amt * s / R;
        vec3 c = vec3(R * (1.0 - cos(th)), 0.0, R * sin(th));
        r = rotY(p, th) + c;
        return mix(lin, r, min(amt, 1.0));
    } else if (mode == 2) {                  // HELIX : two histories wind around the time axis
        float ph = tw * s * 0.22;
        r = p + vec3(R * 0.5 * (cos(ph) - 1.0), R * 0.5 * sin(ph), s);
    } else if (mode == 3) {                  // SPIRAL : radius grows toward the past
        float ph = tw * s * 0.2;
        float rad = R * 0.25 * (1.0 + abs(s) * 0.12);
        r = p + vec3(rad * (cos(ph) - 1.0), rad * sin(ph), s);
    } else if (mode == 4) {                  // VORTEX : slices twist about the sculpture axis
        float ph = tw * s * 0.07;
        float c = cos(ph), sn = sin(ph);
        r = vec3(c * p.x - sn * p.y, sn * p.x + c * p.y, p.z + s);
    } else if (mode == 5) {                  // RING : the history closes into a circle
        float Rr = R * 2.4;
        float th = s / Rr;
        r = rotY(p, th) + vec3(Rr * (1.0 - cos(th)), 0.0, Rr * sin(th));
    } else {                                 // WAVE
        r = p + vec3(R * 0.35 * sin(s * 0.6 * tw * 0.5), R * 0.18 * cos(s * 0.45), s);
    }
    return mix(lin, r, min(amt, 1.0));
}

// ---- Place one stored point of one sample into 3D, with every deformation. ----
struct PB {
    vec3 p;        // final position
    vec4 a0;       // raw P0 (x,y,z,valid)
    vec4 a1;       // rgb, speed
    vec4 a2;       // vel.xy, order, 0
    float inter;   // interaction at that sample
    float age;     // 0 = present .. 1 = oldest of the history
    float s;       // time distance in world units
    vec2 cc;       // contact centre (display coords)
};

vec2 contactCentre(int f) {
    vec4 a = texelFetch(sInfo, ivec2(0, f), 0), b = texelFetch(sInfo, ivec2(1, f), 0);
    vec2 m = 0.5 * (a.xy + b.xy);
    return toDisplayUp(m);
}

PB placeBody(int k, int fi, bool deform) {
    PB o;
    o.a0 = texelFetch(sP0, ivec2(k, fi), 0);
    o.a1 = texelFetch(sP1, ivec2(k, fi), 0);
    o.a2 = texelFetch(sP2, ivec2(k, fi), 0);
    vec4 u0 = U(0);
    float hist = U(1).x;
    o.age = clamp((u0.x - float(fi)) / max(hist - 1.0, 1.0), 0.0, 1.0);
    o.inter = texelFetch(sInfo, ivec2(6, fi), 0).w;
    o.s = (float(fi) - u0.y) * u0.w;
    vec2 d = toDisplay(o.a0.xy);
    float zb = o.a0.z;
    zb = sign(zb) * pow(abs(zb), U(3).y) ;
    vec3 p = vec3(d.x, d.y, zb * U(3).x);
    float sgn = k < NPB ? -1.0 : 1.0;
    p.x += sgn * 0.5 * U(3).w;
    o.cc = contactCentre(fi);
    float clk = U(9).w;
    if (deform) {
        // collision distortion: contact moments push and ripple the surrounding space
        vec2 dir = p.xy - o.cc;
        float dl = length(dir) + 1e-3;
        float I = o.inter;
        float push = I * I * U(5).y * 0.4 * exp(-dl * 0.28);
        p.xy += dir / dl * push * (0.5 + 0.5 * sin(dl * 1.6 - clk * 4.0 - o.age * 6.0));
        p.z += I * U(5).y * 0.35 * sin(dl * 2.0 - clk * 3.0) * exp(-dl * 0.45);
        // temporal curl: swirl around the contact point, growing with age
        float cv = U(6).y;
        if (cv > 0.001) {
            float ang = cv * o.age * 2.2 * exp(-dl * 0.12);
            float cs = cos(ang), sn = sin(ang);
            p.xy = o.cc + vec2(cs * dir.x - sn * dir.y, sn * dir.x + cs * dir.y);
        }
        // noise / turbulence
        float na = U(5).z;
        if (na > 0.001) p += vnoise3(p * U(5).w + vec3(0.0, 0.0, o.s * 0.2) + clk * U(6).x) * na * (0.3 + o.age);
        float tb = U(6).z;
        if (tb > 0.001) p += curl(p * 0.45 + clk * 0.15 * U(6).x + o.s * 0.05) * tb * 0.45 * (0.2 + o.age);
    }
    o.p = timePath(p, o.s);
    return o;
}

vec3 heat(float t) {
    t = clamp(t, 0.0, 1.0);
    return t < 0.5 ? mix(vec3(0.05, 0.25, 1.0), vec3(1.0, 0.9, 0.2), t * 2.0) : mix(vec3(1.0, 0.9, 0.2), vec3(1.0, 0.15, 0.1), (t - 0.5) * 2.0);
}
vec3 timeRamp(float a) {   // present = warm white, past = cyan -> violet
    vec3 c0 = vec3(1.0, 0.92, 0.75), c1 = vec3(0.15, 0.85, 1.0), c2 = vec3(0.55, 0.2, 1.0);
    return a < 0.5 ? mix(c0, c1, a * 2.0) : mix(c1, c2, (a - 0.5) * 2.0);
}


vec3 bodyColor(PB b, int bear, float lum) {
    int cm = int(U(8).w + 0.5);
    vec3 cA = U(13).rgb, cB = U(14).rgb;
    vec3 rgb = b.a1.rgb;
    float speed = b.a1.a;
    if (cm == 0) return pow(rgb, vec3(0.62)) * 1.7 + 0.08;
    if (cm == 1) return vec3(0.35 + lum * 1.6);
    if (cm == 2) return (bear == 0 ? cA : cB) * (0.45 + lum * 1.4);
    if (cm == 3) return timeRamp(b.age) * (0.45 + lum * 1.2);
    if (cm == 4) return heat(speed / 5.0) * (0.5 + lum);
    return mix(vec3(0.15, 0.4, 1.0), vec3(1.0, 0.35, 0.15), b.inter) * (0.45 + lum * 1.3);
}

// far-away cameras need bigger / brighter sprites and lines, otherwise a long sculpture reads as faint dust
float distBoost() { return pow(clamp(U(20).w / 16.7, 1.0, 4.0), 0.75); }
