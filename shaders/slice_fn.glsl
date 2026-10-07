
// instance -> sample index of this time slice, or -1 when outside the visible history
int sliceSample(int inst) {
    vec4 u0 = U(0), u1 = U(1);
    int stp = max(int(u1.y + 0.5), 1);
    int headI = int(floor(u0.x));
    int fi = headI - inst * stp;
    int lo = max(0, headI - int(u1.x + 0.5) + 1);
    if (fi < 0 || fi < lo || fi > int(U(9).z + 0.5)) return -1;
    return fi;
}
