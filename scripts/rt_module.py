"""4D COLLISION runtime (lives in /BEAR_COLLISION/CONTROL_PANEL/rt as a module DAT).
frame() runs every frame: playhead / time direction / freeze, scene automation, camera, uniform texture."""
import math, json, time
import numpy as np

ROOT = 'C:/Users/Utsav/bear-collision'
C = op('/BEAR_COLLISION/CONTROL_PANEL')
UNI = np.zeros((1, 32, 4), np.float32)
HUD = ''
FPS_S = 12.5                       # samples per second
S = {'t_last': None, 'dir': 1.0, 'frozen': False, 'zfrozen': 0.0, 'clock': 0.0, 'orbit_auto': 0.0, 'w': None,
     'scan': 1.0, 'q': None, 'N': 317, 'audio': None, 'err': 0, 'shock_t': 0.0, 'quality_applied': None}

MODE_W = {   # temporal mode -> (points, mesh, slices, slit, contact)
    0: (1.0, 0.35, 0.0, 0.0, 0.6),
    1: (1.0, 0.0, 0.0, 0.0, 0.45),
    2: (0.22, 1.0, 0.0, 0.0, 0.4),
    3: (1.0, 0.0, 1.0, 0.0, 0.2),
    4: (1.0, 0.0, 0.0, 1.0, 0.0),
    5: (0.10, 0.0, 0.0, 0.0, 1.6),
    6: (0.85, 0.7, 0.0, 0.0, 1.0),
}


def P(name):
    return getattr(C.par, name).eval()


def load_meta():
    try:
        m = json.load(open(ROOT + '/data/meta.json'))
        S['N'] = int(m['N'])
    except Exception:
        pass
    try:
        S['audio'] = np.load(ROOT + '/data/info.npy')[:, 8:10, :]
    except Exception:
        S['audio'] = None


QUALITY = {   # sample step, point stride, density, history cap
    'preview': dict(Samplestep=6, Pointstride=1, Pointdensity=0.9),
    'high': dict(Samplestep=3, Pointstride=1, Pointdensity=1.0),
    'cinematic': dict(Samplestep=2, Pointstride=1, Pointdensity=1.0),
}


def apply_quality(name):
    q = QUALITY.get(name)
    if not q: return
    for k, v in q.items():
        getattr(C.par, k).val = v
    S['quality_applied'] = name


def smooth(a, b, k):
    return a + (b - a) * k


TRK = ['bearA_x', 'bearA_y', 'bearB_x', 'bearB_y', 'bear_distance', 'bearA_velocity', 'bearB_velocity', 'relative_velocity', 'interaction_intensity',
       'gap', 'contact', 'bearA_vx', 'bearA_vy', 'bearB_vx', 'bearB_vy', 'bboxA_x0', 'bboxA_y0', 'bboxA_x1', 'bboxA_y1', 'bboxB_x0', 'bboxB_y0', 'bboxB_x1', 'bboxB_y1']


def update_tracking(i):
    inf = S['info'][i]
    vals = [inf[0, 0], inf[0, 1], inf[1, 0], inf[1, 1], inf[6, 0], inf[2, 2], inf[3, 2], inf[6, 2], inf[6, 3], inf[6, 1], inf[9, 1],
            inf[2, 0], inf[2, 1], inf[3, 0], inf[3, 1], *inf[4], *inf[5]]
    ct = op('/BEAR_COLLISION/BEAR_TRACKING/OUT_TRACKING')
    for k, v in enumerate(vals):
        getattr(ct.par, 'value%d' % k).val = float(v)
    for nm, v in zip(['Bearax', 'Bearay', 'Bearbx', 'Bearby', 'Beardistance', 'Bearavelocity', 'Bearbvelocity', 'Relativevelocity', 'Interactionintensity'], vals[:9]):
        getattr(C.par, nm).val = float(v)


REC = C.fetch('REC_STATE', None)
if REC is None:
    REC = {'on': False}
    C.store('REC_STATE', REC)


def rec_start(folder, fps=25, total=None, settle=3, quality='high', skip=0):
    import os
    os.makedirs(folder, exist_ok=True)
    au = op('/BEAR_COLLISION/PERFORMANCE/auto_show').module
    if not au.ST['built']: au.build()
    tot = int(total) if total else int(math.ceil(au.ST['total'] * fps))
    REC.update(on=True, k=0, phase=0, started=False, folder=folder, fps=float(fps), total=tot, P=int(settle), t0=time.perf_counter(), done=False)
    C.par.Qualitymode = quality
    S['quality_applied'] = None
    C.par.Autoquality = 0
    C.par.Autoshow = 1; C.par.Showclock = 0.0; C.par.Showhud = 1; C.par.Playing = 0; C.par.Freezetime = 0; C.par.Docmix = 1
    au.ST.update({'scene': -1, 'run_scene': None})
    S['w'] = None; S['t_last'] = None
    if skip > 0:                                   # fast-forward the (deterministic) show state to frame `skip`
        REC['on'] = False
        S['force_dt'] = 1.0 / fps
        for _ in range(int(skip)):
            _frame()
        S['force_dt'] = None
        S['t_last'] = None
        REC.update(on=True, k=int(skip), phase=0, started=False)
    return tot


def rec_step():
    """called at the top of every _frame while recording: returns the dt to use"""
    ph = REC['phase']
    dt = 0.0
    if ph == 0:
        if REC['started']:
            import os
            fp = '%s/f%05d.jpg' % (REC['folder'], REC['k'])
            for _try in range(4):
                op('/BEAR_COLLISION/RENDER/FINAL_OUT').save(fp)
                if os.path.exists(fp) and os.path.getsize(fp) > 2000: break
                time.sleep(0.05)
            else:
                REC['failed'] = REC.get('failed', 0) + 1
            REC['k'] += 1
            if REC['k'] >= REC['total']:
                REC['on'] = False; REC['done'] = True; S['force_dt'] = None
                C.par.Autoquality = 1
                return None
        dt = 1.0 / REC['fps']
        REC['started'] = True
    REC['phase'] = (ph + 1) % REC['P']
    return dt


def frame():
    try:
        _frame()
    except Exception as e:
        S['err'] += 1
        if S['err'] < 6:
            import traceback
            print('rt error', traceback.format_exc())


def _frame():
    N = S['N']
    last = N - 1
    now = time.perf_counter()                   # wall-clock: playback stays real-time when frames drop
    real = 0.0 if S['t_last'] is None else now - S['t_last']
    dt = min(real, 0.12)
    if REC['on']:
        d_ = rec_step()
        S['force_dt'] = d_
        if d_ is not None: dt = d_
    if S.get('force_dt') is not None: dt = S['force_dt']
    S['t_last'] = now
    if real > 1e-4:
        S['fps'] = 0.92 * S.get('fps', 30.0) + 0.08 * (1.0 / real)
    S['clock'] += dt

    if P('Autoshow'):
        try:
            op('/BEAR_COLLISION/PERFORMANCE/auto_show').module.step(dt, S)
        except Exception:
            S['err'] += 1

    q = C.par.Qualitymode.eval()
    if S['quality_applied'] != q:
        apply_quality(q)

    # ---------------- playhead ----------------
    ph = P('Playhead')
    frozen = bool(P('Freezetime'))
    if frozen and not S['frozen']:
        S['zfrozen'] = ph
    S['frozen'] = frozen
    if P('Playing') and not frozen:
        mode = C.par.Timedirection.eval()
        d = {'forward': 1.0, 'reverse': -1.0}.get(mode, S['dir'] if mode == 'pingpong' else 1.0)
        if mode == 'pingpong': d = S['dir']
        ph += d * dt * FPS_S * P('Playspeed')
        if mode == 'pingpong':
            if ph >= last: ph = last; S['dir'] = -1.0
            elif ph <= 0: ph = 0.0; S['dir'] = 1.0
        else:
            if ph > last: ph = 0.0
            if ph < 0: ph = float(last)
        C.par.Playhead = ph
    ph = min(max(ph, 0.0), float(last))
    # one clock drives every movie: timeline seconds (locked playback) ; +0.25 sample keeps us inside the frame
    if S.get('fcount', 0) % 60 == 0: ensure_timeline()
    root.time.frame = int(round(ph * 2.0)) + 1      # timeline is 25 fps: sample s = source frame 2s (exact, no 60 Hz quantisation)
    C.par.Videoframe = ph * 2.0

    reveal = P('Revealfull')
    head = ph + (last - ph) * reveal
    zref = S['zfrozen'] if frozen else ph
    if frozen or reveal > 0.001:
        if frozen:
            scan = P('Scanpos')
            if P('Scanspeed') > 0:
                scan = (scan + dt * P('Scanspeed') * 0.12) % 1.0
                C.par.Scanpos = scan
            plane = scan * last
        else:
            plane = ph
    else:
        plane = ph
    td_total = P('Timedepth')
    dz = td_total / max(last, 1)

    # ---------------- audio (optional) ----------------
    au = np.zeros(5)
    if P('Audioenable'):
        if C.par.Audiosource.eval() == 'video' and S['audio'] is not None:
            i = int(min(max(ph, 0), len(S['audio']) - 1))
            au = np.array([*S['audio'][i, 0, :4], S['audio'][i, 1, 0]]) * P('Audiogain')
        elif C.par.Audiosource.eval() == 'live':
            try:
                arr = np.asarray(op('/BEAR_COLLISION/AUDIO/OUT_AUDIO_SPECTRUM')[0].numpyArray()).ravel()
                n = len(arr)
                f = lambda lo_, hi_: float(arr[int(n * lo_ / 22050):max(int(n * hi_ / 22050), int(n * lo_ / 22050) + 1)].mean())
                b_, m_, h_ = f(20, 250), f(250, 2000), f(2000, 8000)
                S['aumax'] = max(S.get('aumax', 1e-6) * 0.995, b_, m_, h_, 1e-6)
                tr = max(0.0, b_ - S.get('aubass_prev', 0.0)) / S['aumax']
                S['aubass_prev'] = b_
                au = np.array([b_ / S['aumax'], m_ / S['aumax'], h_ / S['aumax'], min(tr * 4, 1.0), float(arr.mean()) / S['aumax']]) * P('Audiogain')
            except Exception:
                pass
    C.par.Aubass, C.par.Aumid, C.par.Auhigh, C.par.Autransient, C.par.Auamplitude = [float(x) for x in au]
    en = 1.0 if P('Audioenable') else 0.0
    bass, mid, high, trans, amp = au

    # ---------------- weights for the temporal mode ----------------
    mode = int(C.par.Temporalmode.menuIndex)
    tw = np.array(MODE_W[mode], np.float64)
    if S['w'] is None: S['w'] = tw.copy()
    S['w'] = S['w'] + (tw - S['w']) * min(1.0, dt * 5.0)
    w = S['w']

    hist = P('Historylength')
    step = int(P('Samplestep'))
    # adaptive quality: cap the number of time slices so the frame rate holds
    cap = {'preview': 56, 'high': 110, 'cinematic': 220}.get(C.par.Qualitymode.eval(), 56)
    S['nmax'] = min(S.get('nmax', cap), cap)
    S['fcount'] = S.get('fcount', 0) + 1
    if P('Autoquality') and S['fcount'] % 20 == 0 and S.get('force_dt') is None:
        tgt = P('Targetfps')
        if S['fps'] < tgt * 0.85: S['nmax'] = max(14, S['nmax'] * 0.85)
        elif S['fps'] > tgt * 1.5: S['nmax'] = min(cap, S['nmax'] * 1.08)
    if not P('Autoquality'): S['nmax'] = cap
    span = min(hist, head + 1)
    step = max(step, int(math.ceil(span / max(S['nmax'], 1.0))))
    if mode == 3: step = max(1, int(P('Slicespacing')))
    ninst = int(math.ceil(span / step)) + 1
    C.par.Numslices = ninst

    # ---------------- camera ----------------
    S['orbit_auto'] += dt * P('Orbitspeed') if P('Autoorbit') else 0.0
    az = math.radians(P('Camorbit') + S['orbit_auto'])
    el = math.radians(P('Camelevation'))
    dist = P('Camdistance')
    fov = P('Camfov')
    lo = max(0.0, head - hist + 1.0)
    zc = ((lo + head) * 0.5 - zref) * dz
    cb = P('Camcenter')
    if S.get('info') is None:
        S['info'] = np.load(ROOT + '/data/info.npy')
    inf = S['info']
    i0, i1 = int(lo), int(min(head, len(inf) - 1))
    cm = np.load(ROOT + '/data/cam_world.npy') if S.get('cam_map') is None else S['cam_map']
    S['cam_map'] = cm
    cent = 0.5 * (inf[i0:i1 + 1, 0, :2] + inf[i0:i1 + 1, 1, :2])          # y-up stabilised
    ci_ = int(min(max(round(ph), 0), len(cm) - 1))
    a_, b_, tx_, ty_ = cm[ci_]
    q = np.stack([cent[:, 0] - tx_, -cent[:, 1] - ty_], 1)
    sc = max(a_ * a_ + b_ * b_, 1e-6)
    dpx = (a_ * q[:, 0] + b_ * q[:, 1]) / sc
    dpy = -((-b_ * q[:, 0] + a_ * q[:, 1]) / sc)
    cx_, cy_ = float(dpx.mean()), float(dpy.mean())
    tgt = np.array([cx_ * cb, cy_ * cb, zc * cb])
    campos = tgt + dist * np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
    for a, v in zip(('Campx', 'Campy', 'Campz'), campos): getattr(C.par, a).val = float(v)
    for a, v in zip(('Tgtx', 'Tgty', 'Tgtz'), tgt): getattr(C.par, a).val = float(v)
    rh = 720.0
    try:
        rh = float(op('/BEAR_COLLISION/RENDER/render1').height)
    except Exception:
        pass
    projscale = (rh * 0.5) * (16.0 / 9.0) / math.tan(math.radians(fov) * 0.5)
    C.par.Projscale = projscale

    # ---------------- uniform texture ----------------
    cam_map = np.load(ROOT + '/data/cam_world.npy') if S.get('cam_map') is None else S['cam_map']
    S['cam_map'] = cam_map
    ci = int(min(max(round(ph), 0), len(cam_map) - 1))
    camv = cam_map[ci]
    colA = [C.par.Colorar.eval(), C.par.Colorag.eval(), C.par.Colorab.eval()]
    colB = [C.par.Colorbr.eval(), C.par.Colorbg.eval(), C.par.Colorbb.eval()]
    slit_x = (P('Slitpos') - 0.5) * 11.5
    u = UNI[0]
    u[0] = (head, zref, plane, dz * (1.0 + 0.35 * bass * en))
    u[1] = (hist, step, P('Pointstride'), P('Pointdensity'))
    u[2] = (P('Pointsize') * (1.0 + 0.25 * amp * en), P('Splatopacity'), P('Gausslook'), P('Motionstretch'))
    u[3] = (P('Depthscale') * P('Depthinfluence') * 0.55, P('Depthcontrast'), 0.12, P('Bearseparation'))
    u[4] = (mode, int(C.par.Timegeometry.menuIndex), P('Temporalbend') + 0.25 * mid * en, P('Temporaltwist'))
    u[5] = (P('Bendradius'), P('Collisionstrength') * (1.0 + 0.8 * trans * en), P('Noiseamount'), P('Noisescale'))
    u[6] = (P('Noisespeed'), P('Temporalcurl'), P('Turbulence') + 0.5 * high * en, min(1.0, P('Explode') + 0.35 * trans * en))
    u[7] = (P('Explodeforce'), P('Dissolve'), P('Temporalfade'), P('Temporaldecay'))
    u[8] = (P('Pastpersistence'), P('Ageopacity'), P('Agepointsize'), int(C.par.Colormode.menuIndex))
    u[9] = (P('Showa'), P('Showb'), last, S['clock'])
    u[10] = (P('Slicespacing'), P('Slicethickness'), P('Sliceopacity'), P('Slicecount'))
    u[11] = (slit_x, P('Slitwidth') * 11.5, 1.0 if P('Showscanplane') else 0.0, projscale)
    u[12] = camv
    u[13] = (*colA, 0.0)
    u[14] = (*colB, 0.0)
    u[15] = (P('Contactthreshold'), P('Contactpersistence'), P('Contactdensity'), P('Contactwobble'))
    u[16] = (P('Contactbright'), P('Shockspeed'), P('Showcontact'), P('Showshock'))
    u[17] = (bass, mid, high, trans)
    u[18] = (w[0], w[1], w[2], w[3])
    u[19] = (w[4] * P('Showcontact'), P('Dustamount') * P('Showdust'), amp, P('Meshopacity'))
    u[20] = (*campos, dist)
    u[21] = (P('Sourcemix'), P('Showbboxes'), ph, 0.0)
    global HUD
    ii = int(min(max(round(ph), 0), len(S['info']) - 1))
    sec = ph / FPS_S
    perf_txt = '' if REC['on'] else '      %.0f fps   %d slices' % (S.get('fps', 0.0), ninst)
    HUD = ('4D COLLISION  -  TWO BODIES THROUGH TIME' + perf_txt + '\n'
           'T %05.2fs   SAMPLE %03d/%d   INTERACTION %.2f   CONTACT GAP %.2f\n'
           'MODE %s   GEOMETRY %s   TIME DEPTH %.1f   HISTORY %d' %
           (sec, ii, last, S['info'][ii, 6, 3], S['info'][ii, 6, 1], C.par.Temporalmode.eval().upper(), C.par.Timegeometry.eval().upper(), td_total, int(hist)))
    try:
        _h = op('/BEAR_COLLISION/POST_FX/hud_text')
        if _h.par.text.mode != ParMode.CONSTANT: _h.par.text.mode = ParMode.CONSTANT
        if _h.par.text.val != HUD: _h.par.text = HUD
    except Exception:
        pass
    try:
        update_tracking(ii)
    except Exception:
        pass
    try:
        op('/BEAR_COLLISION/TEMPORAL_BUFFER/uni_tex').cook(force=True)
    except Exception:
        pass


def ensure_timeline():
    t = root.time
    if t.rangeEnd < 100000 or t.loop:
        t.rangeStart = 1; t.rangeEnd = 360000; t.end = 360000; t.loop = False
    if abs(t.rate - 25.0) > 1e-6:
        t.rate = 25.0
    if not t.play:
        t.play = True


ensure_timeline()
load_meta()
