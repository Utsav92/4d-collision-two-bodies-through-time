"""Stage B for 4D COLLISION: from the Stage-A cache build tracked bear masks (A/B), stabilised point clouds,
interaction signals, contact pairs, shockwave events, audio features, and the float textures TouchDesigner loads.
usage: python pack_bears.py [nlimit] [--debug]
"""
import os, sys, json, subprocess, glob
import numpy as np, cv2
from scipy.optimize import linear_sum_assignment
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'work', 'cache')
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)
VIDEO = r'C:\Users\Utsav\Downloads\07.10.2026_03.14.43_REC.mp4'
meta = json.load(open(os.path.join(CACHE, 'meta.json'))) if os.path.exists(os.path.join(CACHE, 'meta.json')) else {'H': 574, 'W': 1150, 'lh': 287, 'LOW_W': 575, 'STEP': 2, 'CROP': [0, 574, 0, 1150]}
H, W, LH, LW, STEP = meta['H'], meta['W'], meta['lh'], meta['LOW_W'], meta['STEP']
UNIT = 50.0                       # half-res px per world unit  (image height 287px -> 5.74 units)
CX, CY = LW / 2.0, LH / 2.0
NIN, NCON = 640, 128              # interior / contour points per bear
NPB = NIN + NCON                  # 768
NPT = NPB * 2                     # 1536
KPAIR = 192
DT = STEP / 25.0                  # seconds between samples
args = [a for a in sys.argv[1:] if not a.startswith('--')]
NLIM = int(args[0]) if args else 10**9
DEBUG = '--debug' in sys.argv
ANIMAL = set(range(16, 26))

files = sorted(glob.glob(os.path.join(CACHE, 'frame_*.npz')))
N = min(len(files), NLIM)
cam_all = np.load(os.path.join(CACHE, 'camera.npy'))
print('samples', N, flush=True)

# ---------------------------------------------------------------- video frames (crop) for colours
cap = cv2.VideoCapture(VIDEO)
frames, i = [], 0
while len(frames) < N:
    ok, f = cap.read()
    if not ok: break
    if i % STEP == 0:
        frames.append(f[0:H, 0:W].copy())
    i += 1
N = min(N, len(frames))

# ---------------------------------------------------------------- cumulative camera (frame t -> frame 0), centred units
C = [np.eye(3)]
for t in range(1, N):
    A = np.vstack([cam_all[t], [0, 0, 1]]).astype(np.float64)
    C.append(C[-1] @ A)
C = np.array(C)


def sim_params(M):
    """M: 3x3 in half-res px -> (a, b, tcx, tcy) in centred /UNIT coordinates"""
    a, b = (M[0, 0] + M[1, 1]) / 2.0, (M[1, 0] - M[0, 1]) / 2.0
    Rm = np.array([[a, -b], [b, a]])
    tc = M[:2, 2] + Rm @ np.array([CX, CY]) - np.array([CX, CY])
    return np.array([a, b, tc[0] / UNIT, tc[1] / UNIT])


# ---------------------------------------------------------------- per-sample foreground + identity
def load(t):
    z = np.load(files[t])
    m = np.unpackbits(z['masks'], axis=-1)[:, :, :W].astype(bool) if len(z['masks']) else np.zeros((0, H, W), bool)
    return dict(boxes=z['boxes'], labels=z['labels'], scores=z['scores'], masks=m, depth=z['depth'].astype(np.float32), flow=z['flow'].astype(np.float32))


def union_instances(d):
    """dedupe overlapping instances (keep highest score), drop tiny"""
    order = np.argsort(-d['scores'])
    kept, acc = [], np.zeros((H, W), bool)
    for k in order:
        if int(d['labels'][k]) not in ANIMAL: continue
        m = d['masks'][k]
        a = m.sum()
        if a < 1500: continue
        ov = (m & acc).sum() / max(a, 1)
        if ov > 0.55: continue
        kept.append(m & ~acc if ov > 0.0 else m)
        acc |= m
    return kept, acc


def lab_L(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)


def feat(img_lab, ys, xs):
    return np.stack([xs / float(H), ys / float(H), img_lab[ys, xs, 0] / 255.0 * 1.2, img_lab[ys, xs, 1] / 255.0 * 0.8 + img_lab[ys, xs, 2] / 255.0 * 0.8], 1)


def kmeans_split(img_lab, union, centers, iters=6):
    ys, xs = np.nonzero(union)
    if len(ys) < 50:
        return np.zeros(len(ys), np.int8), ys, xs, centers
    F = feat(img_lab, ys, xs)
    c = centers.copy()
    for _ in range(iters):
        d = ((F[:, None, :] - c[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(2):
            if (lab == j).sum() > 20: c[j] = F[lab == j].mean(0)
    return lab.astype(np.int8), ys, xs, c


def clean(m, keep_near=True):
    m = m.astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1: return m.astype(bool)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    out = lab == big
    for k in range(1, n):
        if k != big and st[k, cv2.CC_STAT_AREA] > 0.04 * st[big, cv2.CC_STAT_AREA]:
            out |= lab == k
    return ndi.binary_fill_holes(out)


state = {'cent': None, 'feat': None, 'area': None, 'vel': np.zeros((2, 2))}
MA = np.zeros((N, H, W), bool); MB = np.zeros((N, H, W), bool)
mode = []
for t in range(N):
    d = load(t)
    kept, acc = union_instances(d)
    img_lab = cv2.cvtColor(frames[t], cv2.COLOR_BGR2LAB)
    if t == 0 or state['cent'] is None:
        # initial: left = A, right = B
        if len(kept) >= 2:
            ks = sorted(kept, key=lambda m: -m.sum())[:2]
            ks = sorted(ks, key=lambda m: np.nonzero(m)[1].mean())
            a_m, b_m = ks
        else:
            union = acc
            ys, xs = np.nonzero(union)
            cx = np.median(xs)
            Fn = feat(img_lab, ys, xs)
            c0 = np.array([Fn[xs < cx].mean(0), Fn[xs >= cx].mean(0)])
            lab, ys, xs, _ = kmeans_split(img_lab, union, c0)
            a_m = np.zeros((H, W), bool); b_m = np.zeros((H, W), bool)
            a_m[ys[lab == 0], xs[lab == 0]] = True; b_m[ys[lab == 1], xs[lab == 1]] = True
        mode.append('init')
    else:
        pa, pb = state['cent'][0] + state['vel'][0], state['cent'][1] + state['vel'][1]
        areas = np.array([k.sum() for k in kept]) if kept else np.zeros(0)
        pr_area = state['area']
        use_two = False
        if len(kept) >= 2:
            ks = sorted(kept, key=lambda m: -m.sum())[:2]
            if all(k.sum() > 0.30 * pr_area[j] for j, k in enumerate(sorted(ks, key=lambda m: np.nonzero(m)[1].mean()))) and (ks[0] | ks[1]).sum() < 1.5 * pr_area.sum():
                use_two = True
        if use_two:
            cents = [np.array([np.nonzero(k)[1].mean(), np.nonzero(k)[0].mean()]) for k in ks]
            cols = [np.concatenate([img_lab[k][:, :1].mean(0), img_lab[k][:, 1:].mean(0)]) for k in ks]
            cost = np.zeros((2, 2))
            for i_ in range(2):
                for j in range(2):
                    cost[i_, j] = np.linalg.norm(cents[j] - [pa, pb][i_]) / H + 0.6 * abs(img_lab[ks[j]][:, 0].mean() / 255.0 * 1.2 - state['feat'][i_][2])
            r, cidx = linear_sum_assignment(cost)
            a_m, b_m = ks[cidx[0]].copy(), ks[cidx[1]].copy()
            ov = a_m & b_m
            if ov.any():
                oy, ox = np.nonzero(ov)
                F = feat(img_lab, oy, ox)
                dA = ((F - state['feat'][0]) ** 2).sum(1); dB = ((F - state['feat'][1]) ** 2).sum(1)
                a_m[oy[dB < dA], ox[dB < dA]] = False; b_m[oy[dA <= dB], ox[dA <= dB]] = False
            # leftover pixels from other instances join the nearest bear
            rest = acc & ~(a_m | b_m)
            if rest.any():
                ry, rx = np.nonzero(rest)
                dA = (rx - state['cent'][0][0]) ** 2 + (ry - state['cent'][0][1]) ** 2
                dB = (rx - state['cent'][1][0]) ** 2 + (ry - state['cent'][1][1]) ** 2
                a_m[ry[dA <= dB], rx[dA <= dB]] = True; b_m[ry[dA > dB], rx[dA > dB]] = True
            mode.append('two')
        else:
            union = acc if acc.sum() > 800 else (state['lastunion'] if 'lastunion' in state else acc)
            lab, ys, xs, c = kmeans_split(img_lab, union, state['feat'].copy())
            a_m = np.zeros((H, W), bool); b_m = np.zeros((H, W), bool)
            a_m[ys[lab == 0], xs[lab == 0]] = True; b_m[ys[lab == 1], xs[lab == 1]] = True
            # flow-warped previous masks are a strong prior where unambiguous
            fl2 = cv2.resize(d['flow'], (W, H), interpolation=cv2.INTER_LINEAR) * 2.0
            gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
            mx, my = gx - fl2[..., 0], gy - fl2[..., 1]
            wa = cv2.remap(MA[t - 1].astype(np.uint8), mx, my, cv2.INTER_NEAREST) > 0
            wb = cv2.remap(MB[t - 1].astype(np.uint8), mx, my, cv2.INTER_NEAREST) > 0
            uu = a_m | b_m
            onlyA, onlyB = uu & wa & ~wb, uu & wb & ~wa
            a_m = (a_m & ~onlyB) | onlyA; b_m = (b_m & ~onlyA) | onlyB
            # spatial regularisation: majority filter on the A/B label inside the union removes speckled assignments
            uu = a_m | b_m
            am = cv2.medianBlur((a_m.astype(np.uint8) * 255), 31) > 127
            a_m = am & uu; b_m = uu & ~a_m
            mode.append('split')
    a_m, b_m = clean(a_m), clean(b_m)
    state['lastunion'] = a_m | b_m
    cen = []
    for m in (a_m, b_m):
        ys, xs = np.nonzero(m)
        cen.append(np.array([xs.mean(), ys.mean()]) if len(ys) > 20 else (state['cent'][len(cen)] if state['cent'] is not None else np.array([W / 2, H / 2])))
    ftr = []
    for j, m in enumerate((a_m, b_m)):
        ys, xs = np.nonzero(m)
        if len(ys) > 200:
            sel = np.random.RandomState(0).choice(len(ys), min(len(ys), 3000), replace=False)
            ftr.append(feat(img_lab, ys[sel], xs[sel]).mean(0))
        else:
            ftr.append(state['feat'][j] if state['feat'] is not None else np.zeros(4))
    ftr = np.array(ftr)
    if state['feat'] is not None: ftr = 0.7 * state['feat'] + 0.3 * ftr
    if state['cent'] is not None:
        state['vel'] = 0.5 * state['vel'] + 0.5 * (np.array(cen) - state['cent'])
    state['cent'] = np.array(cen); state['feat'] = ftr; state['area'] = np.array([a_m.sum(), b_m.sum()], np.float64)
    MA[t], MB[t] = a_m, b_m
    if t % 25 == 0: print('track', t, mode[-1], a_m.sum(), b_m.sum(), flush=True)

# ---------------------------------------------------------------- point sampling
def halton(n, b):
    out = np.zeros(n)
    for i in range(n):
        f, r, k = 1.0, 0.0, i + 1
        while k > 0:
            f /= b; r += f * (k % b); k //= b
        out[i] = r
    return out


HX, HY = halton(6000, 2), halton(6000, 3)
rng = np.random.RandomState(7)


def sample_bear(mask, depth_n, rgb, flow, Cprev_lin, Ar, t):
    """returns (NPB, 4) pos(x,y,z,valid), (NPB,4) rgb+speed, (NPB,4) vel+extra"""
    pos = np.zeros((NPB, 4), np.float32); col = np.zeros((NPB, 4), np.float32); vel = np.zeros((NPB, 4), np.float32)
    ys, xs = np.nonzero(mask)
    if len(ys) < 300: return pos, col, vel
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    cx = (x0 + HX * (x1 - x0)).astype(int).clip(0, W - 1); cy = (y0 + HY * (y1 - y0)).astype(int).clip(0, H - 1)
    ok = mask[cy, cx]
    sel = np.nonzero(ok)[0][:NIN]
    px = list(cx[sel]); py = list(cy[sel])
    if len(px) < NIN:
        extra = rng.choice(len(ys), NIN - len(px))
        px += list(xs[extra]); py += list(ys[extra])
    px = np.array(px, float) + rng.uniform(-0.4, 0.4, NIN); py = np.array(py, float) + rng.uniform(-0.4, 0.4, NIN)
    # contour
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs = max(cs, key=len)[:, 0, :].astype(np.float64)
    start = int(np.argmin(cs[:, 1]))
    cs = np.roll(cs, -start, axis=0)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(cs, axis=0), axis=1))]
    tt = np.linspace(0, seg[-1], NCON, endpoint=False)
    cxy = np.stack([np.interp(tt, seg, cs[:, 0]), np.interp(tt, seg, cs[:, 1])], 1)
    ax = np.r_[px, cxy[:, 0]]; ay = np.r_[py, cxy[:, 1]]
    ix = ax.astype(int).clip(0, W - 1); iy = ay.astype(int).clip(0, H - 1)
    lx = (ax / 2.0).clip(0, LW - 1.001); ly = (ay / 2.0).clip(0, LH - 1.001)
    lxi, lyi = lx.astype(int), ly.astype(int)
    # stabilised world position (half-res px -> frame 0 -> centred units)
    Ct = C[t]
    p0 = (Ct[:2, :2] @ np.stack([lx, ly]) + Ct[:2, 2:3])
    X = (p0[0] - CX) / UNIT; Y = (p0[1] - CY) / UNIT
    Z = depth_n[lyi, lxi]
    # camera-compensated object velocity (half-res px per sample) -> units/s
    f = flow[lyi, lxi]                                        # (n,2) prev->cur at pixel
    if t > 0:
        Ap = Ar                                               # 2x3 frame t -> frame t-1
        cam_disp = (Ap[:, :2] @ np.stack([lx, ly]) + Ap[:, 2:3]).T - np.stack([lx, ly]).T
        v_loc = f + cam_disp
        v0 = (Cprev_lin @ v_loc.T).T / UNIT / DT
    else:
        v0 = np.zeros((NPB, 2))
    pos[:, 0], pos[:, 1], pos[:, 2], pos[:, 3] = X, Y, Z, 1.0
    rgbv = frames[t][iy, ix][:, ::-1].astype(np.float32) / 255.0
    col[:, :3] = rgbv; col[:, 3] = np.linalg.norm(v0, axis=1)
    vel[:, 0], vel[:, 1] = v0[:, 0], -v0[:, 1]
    vel[:, 2] = np.linspace(0, 1, NPB)                       # point order (0..1) for shader hashing
    vel[:, 3] = 0.0
    return pos, col, vel


T0 = np.zeros((N, NPT, 4), np.float32); T1 = np.zeros((N, NPT, 4), np.float32); T2 = np.zeros((N, NPT, 4), np.float32)
INFO_W = 10
INFO = np.zeros((N, INFO_W, 4), np.float32)
cent_w = np.zeros((N, 2, 2)); bbox_w = np.zeros((N, 2, 4)); area_w = np.zeros((N, 2)); gap = np.zeros(N); dist = np.zeros(N)
vel_w = np.zeros((N, 2, 2)); height = np.zeros(N)
pairs = np.zeros((N, KPAIR, 4), np.float32)
depth_vid = np.zeros((N, LH, LW), np.uint8)
flow_vid = np.zeros((N, LH, LW, 3), np.uint8)

for t in range(N):
    d = load(t)
    dep = d['depth'].astype(np.float32)
    lo, hi = np.percentile(dep, 2), np.percentile(dep, 98)
    dn_full = (dep - lo) / max(hi - lo, 1e-6)
    uni = cv2.resize((MA[t] | MB[t]).astype(np.uint8), (LW, LH), interpolation=cv2.INTER_NEAREST) > 0
    med = np.median(dn_full[uni]) if uni.any() else 0.5
    depth_n = (dn_full - med) * 3.0
    depth_vid[t] = (dn_full.clip(0, 1) * 255).astype(np.uint8)
    fl = d['flow']
    ang = np.arctan2(fl[..., 1], fl[..., 0]); mag = np.linalg.norm(fl, axis=-1)
    hsv = np.stack([((ang + np.pi) / (2 * np.pi) * 179).astype(np.uint8), np.full(mag.shape, 255, np.uint8), (mag * 40).clip(0, 255).astype(np.uint8)], -1)
    flow_vid[t] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    Cprev_lin = C[t - 1][:2, :2] if t > 0 else np.eye(2)
    Ar = cam_all[t]
    for j, m in enumerate((MA[t], MB[t])):
        pos, col, vel = sample_bear(m, depth_n, frames[t], d['flow'], Cprev_lin, Ar, t)
        sl = slice(j * NPB, (j + 1) * NPB)
        T0[t, sl], T1[t, sl], T2[t, sl] = pos, col, vel
        ys, xs = np.nonzero(m)
        if len(ys) > 300:
            p = (C[t][:2, :2] @ np.array([xs / 2.0, ys / 2.0]) + C[t][:2, 2:3])
            Xs, Ys = (p[0] - CX) / UNIT, -(p[1] - CY) / UNIT
            cent_w[t, j] = [Xs.mean(), Ys.mean()]
            bbox_w[t, j] = [Xs.min(), Ys.min(), Xs.max(), Ys.max()]
            area_w[t, j] = len(ys) / 4.0 / UNIT ** 2
            vel_w[t, j] = [np.nanmean(pos_v) for pos_v in (vel[:NIN, 0], vel[:NIN, 1])]
        else:
            cent_w[t, j] = cent_w[t - 1, j] if t else 0
    height[t] = np.mean([bbox_w[t, 0, 3] - bbox_w[t, 0, 1], bbox_w[t, 1, 3] - bbox_w[t, 1, 1]])
    dist[t] = np.linalg.norm(cent_w[t, 0] - cent_w[t, 1])
    # mask gap
    dtB = cv2.distanceTransform((~MB[t]).astype(np.uint8), cv2.DIST_L2, 3)
    gap[t] = dtB[MA[t]].min() / 2.0 / UNIT if MA[t].any() else 9.0
    # contact pairs: nearest B point for each A point (x,y + 0.35 z)
    A = T0[t, :NPB, :3] * [1, 1, 0.35]; B = T0[t, NPB:, :3] * [1, 1, 0.35]
    if T0[t, 0, 3] > 0 and T0[t, NPB, 3] > 0:
        dd = ((A[:, None] - B[None]) ** 2).sum(-1)
        j = dd.argmin(1); md = np.sqrt(dd[np.arange(NPB), j])
        order = np.argsort(md)[:KPAIR]
        pairs[t, :, 0] = order; pairs[t, :, 1] = j[order]; pairs[t, :, 2] = md[order]; pairs[t, :, 3] = 1.0
    if t % 25 == 0: print('pack', t, flush=True)

# ---------------------------------------------------------------- interaction signal
vel_c = np.zeros((N, 2, 2)); speed = np.zeros((N, 2))
for t in range(1, N):
    vel_c[t] = (cent_w[t] - cent_w[t - 1]) / DT
sm = lambda x, k: ndi.uniform_filter1d(x, k, axis=0, mode='nearest')
vel_c = sm(vel_c, 3)
speed = np.linalg.norm(vel_c, axis=-1)
relvel = np.zeros(N)
dist_s = sm(dist, 3)
relvel[1:] = -(dist_s[1:] - dist_s[:-1]) / DT
hb = max(np.median(height), 0.5)
nd = np.clip(dist_s / (1.5 * hb), 0, 1)
g = 1 - np.clip(gap / (0.35 * hb), 0, 1)
ap = np.clip(relvel / (1.2 * hb), 0, 1)
inter = np.clip(0.45 * (1 - nd) ** 1.2 + 0.40 * g + 0.15 * ap, 0, 1)
inter = ndi.gaussian_filter1d(inter, 1.0, mode='nearest')
lo_, hi_ = np.percentile(inter, 5), np.percentile(inter, 99)
inter = np.clip((inter - lo_) / max(hi_ - lo_, 1e-6), 0, 1)
contact = (gap < 0.06 * hb).astype(np.float32)

# events = local maxima of interaction
events = []
for t in range(2, N - 2):
    if inter[t] > 0.62 and inter[t] == inter[max(0, t - 8):t + 9].max():
        if not events or t - events[-1][0] > 10:
            ev_pos = 0.5 * (cent_w[t, 0] + cent_w[t, 1])
            events.append((t, ev_pos[0], ev_pos[1], inter[t]))
events = events[:16]
EV = np.zeros((16, 4), np.float32)
for i, e in enumerate(events): EV[i] = e
print('events', [(e[0], round(e[3], 2)) for e in events], flush=True)

# ---------------------------------------------------------------- audio features
wav = os.path.join(ROOT, 'work', 'audio.wav')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', VIDEO, '-vn', '-ac', '1', '-ar', '16000', wav], check=False)
audio = np.zeros((N, 5), np.float32)
try:
    import wave
    w = wave.open(wav); sr = w.getframerate(); sig = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    prev = None
    for t in range(N):
        c = int((t * STEP / 25.0) * sr); seg = sig[max(0, c - 640): c + 640]
        if len(seg) < 256: continue
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1 / sr)
        b = S[(fr > 20) & (fr < 250)].mean(); m = S[(fr >= 250) & (fr < 2000)].mean(); h = S[(fr >= 2000) & (fr < 8000)].mean()
        flux = 0 if prev is None else np.maximum(S[:len(prev)] - prev[:len(S)], 0).sum() / len(S)
        prev = S
        audio[t] = [b, m, h, flux, np.sqrt((seg ** 2).mean())]
    for k in range(5):
        audio[:, k] = np.clip(audio[:, k] / max(np.percentile(audio[:, k], 98), 1e-9), 0, 1)
except Exception as e:
    print('audio failed', e)

# ---------------------------------------------------------------- info texture
for t in range(N):
    INFO[t, 0] = [cent_w[t, 0, 0], cent_w[t, 0, 1], area_w[t, 0], float(T0[t, 0, 3])]
    INFO[t, 1] = [cent_w[t, 1, 0], cent_w[t, 1, 1], area_w[t, 1], float(T0[t, NPB, 3])]
    INFO[t, 2] = [vel_c[t, 0, 0], vel_c[t, 0, 1], speed[t, 0], 0]
    INFO[t, 3] = [vel_c[t, 1, 0], vel_c[t, 1, 1], speed[t, 1], 0]
    INFO[t, 4] = bbox_w[t, 0]; INFO[t, 5] = bbox_w[t, 1]
    INFO[t, 6] = [dist[t], gap[t], relvel[t], inter[t]]
    INFO[t, 7] = sim_params(C[t])
    INFO[t, 8] = audio[t, :4]
    INFO[t, 9] = [audio[t, 4], contact[t], sum(1 for e in events if e[0] == t) * 1.0, 0]

np.save(os.path.join(DATA, 'pts0.npy'), T0); np.save(os.path.join(DATA, 'pts1.npy'), T1); np.save(os.path.join(DATA, 'pts2.npy'), T2)
np.save(os.path.join(DATA, 'info.npy'), INFO); np.save(os.path.join(DATA, 'pairs.npy'), pairs); np.save(os.path.join(DATA, 'events.npy'), EV)
np.save(os.path.join(DATA, 'cam_world.npy'), np.array([sim_params(c) for c in C], np.float32))
# CHOP-friendly table
import csv
with open(os.path.join(DATA, 'tracking.csv'), 'w', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['bearA_x', 'bearA_y', 'bearB_x', 'bearB_y', 'bear_distance', 'bearA_velocity', 'bearB_velocity', 'relative_velocity', 'interaction_intensity', 'gap', 'contact',
                 'bboxA_x0', 'bboxA_y0', 'bboxA_x1', 'bboxA_y1', 'bboxB_x0', 'bboxB_y0', 'bboxB_x1', 'bboxB_y1', 'audio_bass', 'audio_mid', 'audio_high', 'audio_transient', 'audio_amp'])
    for t in range(N):
        wr.writerow([*cent_w[t, 0], *cent_w[t, 1], dist[t], speed[t, 0], speed[t, 1], relvel[t], inter[t], gap[t], contact[t], *bbox_w[t, 0], *bbox_w[t, 1], *audio[t]])
json.dump({'N': N, 'NPB': NPB, 'NPT': NPT, 'NIN': NIN, 'NCON': NCON, 'KPAIR': KPAIR, 'UNIT': UNIT, 'H': H, 'W': W, 'LH': LH, 'LW': LW, 'STEP': STEP, 'DT': DT,
           'events': [list(map(float, e)) for e in events], 'height': float(hb), 'modes': {m: mode.count(m) for m in set(mode)}},
          open(os.path.join(DATA, 'meta.json'), 'w'))

# ---------------------------------------------------------------- mask / depth / flow videos (sample-indexed, 25 fps container)
def write_video(name, gen, crf=6, pix='yuv420p'):
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % gen[1], '-r', '12.5', '-i', '-',
                          '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-crf', str(crf), '-g', '1', '-pix_fmt', pix, os.path.join(DATA, name)], stdin=subprocess.PIPE)
    for fr in gen[0]:
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close(); p.wait()


def mask_frames():
    for t in range(N):
        fr = np.zeros((H, W, 3), np.uint8)
        fr[..., 2] = MA[t] * 255; fr[..., 1] = MB[t] * 255; fr[..., 0] = (MA[t] | MB[t]) * 255   # BGR: R=A, G=B, B=union
        yield fr


write_video('mask.mp4', (mask_frames(), (W, H)))
write_video('depth.mp4', ((cv2.cvtColor(depth_vid[t], cv2.COLOR_GRAY2BGR) for t in range(N)), (LW, LH)), crf=8)
write_video('flow.mp4', ((flow_vid[t] for t in range(N)), (LW, LH)), crf=10)

if DEBUG:
    os.makedirs(os.path.join(ROOT, 'work', 'dbg'), exist_ok=True)
    for t in range(0, N, max(1, N // 12)):
        im = frames[t].copy()
        ov = im.copy(); ov[MA[t]] = (0.3 * ov[MA[t]] + 0.7 * np.array([30, 140, 255])).astype(np.uint8)
        ov[MB[t]] = (0.3 * ov[MB[t]] + 0.7 * np.array([255, 170, 30])).astype(np.uint8)
        cv2.putText(ov, 't%d %s inter %.2f gap %.2f' % (t, mode[t], inter[t], gap[t]), (10, 24), 0, 0.7, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(ROOT, 'work', 'dbg', 'trk_%03d.jpg' % t), cv2.resize(ov, (575, 287)))
print('PACK DONE', N, flush=True)
