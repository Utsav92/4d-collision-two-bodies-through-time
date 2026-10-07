"""AUTO_SHOW : the 14-scene performance, driven by keyframes on the real control parameters.
step(dt, S) is called by rt.frame() while AUTO_SHOW is on. SHOW_CLOCK (CONTROL_PANEL) is the master clock, set it to jump."""
import numpy as np

C = op('/BEAR_COLLISION/CONTROL_PANEL')
FPS_S = 12.5
ST = {'scene': -1, 'start_vals': {}, 'peaks': None, 'built': False, 'scenes': None}


def peaks():
    """Pick the narrative anchor samples from the tracked interaction signal."""
    import json
    info = np.load('C:/Users/Utsav/bear-collision/data/info.npy')
    inter = info[:, 6, 3]
    n = len(inter)
    sm = np.convolve(inter, np.ones(7) / 7.0, mode='same')
    ev = np.load('C:/Users/Utsav/bear-collision/data/events.npy')
    ev = [int(e[0]) for e in ev if e[3] > 0]
    # S1: strong grappling moment in the first ~55% (upright hug)  | SP: strongest of the whole fight
    lim = int(n * 0.55)
    s1 = int(np.argmax(sm[20:lim]) + 20)
    sp = int(np.argmax(sm))
    return {'n': n, 'last': n - 1, 's1': s1, 'sp': sp, 'events': ev, 'inter': sm}


def build():
    pk = peaks()
    ST['peaks'] = pk
    n, last, s1, sp = pk['n'], pk['last'], pk['s1'], pk['sp']
    ra = max(0, sp - 45); rb = min(last, sp + 25)
    # each scene: name, duration, params (value or [(frac, value)...]), play spec
    # play spec: ('run', start, speed) | ('hold', sample) | ('replay', a, b, speed)
    SC = [
        ('01 DOCUMENTARY', 14.0, dict(Docmix=1.0, Freezetime=0, Sourcemix=0.0, Timedepth=0.0, Camorbit=0.0, Camelevation=0.0, Camdistance=16.7, Camcenter=0.0,
                                     Revealfull=0.0, Fadeblack=[(0.0, 1.0), (0.06, 0.0)], Temporalmode='pointcloud', Timegeometry='linear', Temporalbend=1.0,
                                     Explode=0.0, Dissolve=0.0, Showcontact=0, Colormode='original', Bearseparation=0.0, Collisionstrength=1.0),
         ('run', 0.0, 1.0)),
        ('02 FREEZE', 6.0, dict(Docmix=[(0.0, 1.0), (0.45, 0.0)], Freezetime=1, Sourcemix=[(0.0, 0.0), (0.4, 0.9), (1.0, 0.7)], Timedepth=0.0, Showscanplane=1, Splatopacity=1.6, Pointsize=1.35, Samplestep=3),
         ('hold', float(s1))),
        ('03 CAMERA MOVES', 10.0, dict(Docmix=0.0, Sourcemix=[(0.0, 0.7), (1.0, 0.35)], Camorbit=[(0.0, 0.0), (1.0, 38.0)], Camelevation=[(0.0, 0.0), (1.0, 8.0)],
                                      Timedepth=[(0.0, 0.0), (1.0, 6.0)], Camdistance=[(0.0, 16.7), (1.0, 20.0)], Temporalmode='pointcloud', Splatopacity=1.5, Pointsize=1.3),
         ('hold', float(s1))),
        ('04 TIME REVEALED', 14.0, dict(Timedepth=[(0.0, 6.0), (0.7, 36.0), (1.0, 36.0)], Camorbit=[(0.0, 38.0), (1.0, 92.0)], Camelevation=[(0.0, 8.0), (1.0, 6.0)],
                                       Camdistance=[(0.0, 20.0), (1.0, 38.0)], Camcenter=[(0.0, 0.0), (0.6, 1.0)], Sourcemix=[(0.0, 0.35), (0.5, 0.0)], Samplestep=3, Splatopacity=1.1, Pointsize=1.0),
         ('hold', float(s1))),
        ('05 TWO HISTORIES', 12.0, dict(Colormode='twocolors', Bearseparation=[(0.0, 0.0), (0.7, 1.4)], Camorbit=[(0.0, 92.0), (1.0, 128.0)], Camelevation=[(0.0, 6.0), (1.0, 22.0)],
                                       Showcontact=0, Meshopacity=0.5),
         ('hold', float(s1))),
        ('06 CONTACT MEMORY', 14.0, dict(Showcontact=1, Temporalmode='hybrid', Contactpersistence=1.0, Contactthreshold=0.75, Revealfull=[(0.0, 0.0), (0.5, 1.0)],
                                        Timedepth=[(0.0, 36.0), (1.0, 48.0)], Camorbit=[(0.0, 128.0), (1.0, 165.0)], Camdistance=[(0.0, 40.0), (1.0, 46.0)],
                                        Scanspeed=1.0, Bearseparation=[(0.0, 1.4), (1.0, 0.6)], Contactbright=1.4),
         ('hold', float(s1))),
        ('07 POINT CLOUD', 10.0, dict(Temporalmode='pointcloud', Colormode='original', Gausslook=1.0, Pointsize=[(0.0, 1.0), (1.0, 1.4)], Camorbit=[(0.0, 165.0), (1.0, 205.0)],
                                     Camelevation=[(0.0, 22.0), (1.0, 12.0)], Showcontact=1, Bearseparation=0.0),
         ('hold', float(s1))),
        ('08 TIME BENDS', 16.0, dict(Timegeometry='curve', Temporalbend=[(0.0, 0.0), (0.4, 1.0)], Bendradius=[(0.0, 14.0), (0.45, 9.0), (1.0, 5.0)],
                                    Temporaltwist=[(0.0, 1.0), (1.0, 2.2)], Camorbit=[(0.0, 205.0), (1.0, 250.0)], Camdistance=[(0.0, 46.0), (1.0, 52.0)],
                                    Colormode='timegradient', Timedepth=48.0),
         ('hold', float(s1))),
        ('09 COLLISION FIELD', 14.0, dict(Timegeometry='linear', Temporalbend=1.0, Colormode='interaction', Freezetime=0, Revealfull=0.0, Collisionstrength=2.6, Shockspeed=1.6,
                                         Showshock=1, Timedepth=26.0, Camorbit=[(0.0, 250.0), (1.0, 330.0)], Camdistance=[(0.0, 52.0), (1.0, 22.0)], Camcenter=[(0.0, 1.0), (1.0, 1.0)],
                                         Temporalmode='hybrid', Samplestep=3),
         ('replay', float(ra), float(rb), 1.0)),
        ('10 TEMPORAL EXPLOSION', 8.0, dict(Explode=[(0.0, 0.0), (0.3, 1.0), (1.0, 1.0)], Explodeforce=14.0, Turbulence=[(0.0, 0.0), (0.4, 1.4)], Camdistance=[(0.0, 22.0), (1.0, 38.0)],
                                           Camorbit=[(0.0, 330.0), (1.0, 380.0)], Colormode='velocity', Timedepth=34.0, Revealfull=[(0.0, 0.0), (0.4, 1.0)], Freezetime=[(0.0, 0), (0.1, 1)]),
         ('hold', float(sp))),
        ('11 CONTACT REMAINS', 10.0, dict(Dissolve=[(0.0, 0.0), (0.7, 1.0)], Explode=[(0.0, 1.0), (0.8, 0.0)], Temporalmode='contactfield', Showcontact=1, Contactpersistence=1.0,
                                         Contactthreshold=0.9, Turbulence=0.3, Camorbit=[(0.0, 20.0), (1.0, 60.0)], Camdistance=[(0.0, 38.0), (1.0, 44.0)], Colormode='twocolors',
                                         Contactbright=1.8, Timedepth=44.0),
         ('hold', float(sp))),
        ('12 RECONSTRUCTION', 10.0, dict(Dissolve=[(0.0, 1.0), (0.8, 0.0)], Explode=0.0, Turbulence=0.0, Temporalmode='hybrid', Colormode='twocolors', Meshopacity=0.28, Splatopacity=0.7,
                                        Camorbit=[(0.0, 60.0), (1.0, 100.0)], Timedepth=[(0.0, 44.0), (1.0, 50.0)], Contactbright=1.0),
         ('hold', float(sp))),
        ('13 COLLAPSE TIME', 10.0, dict(Timedepth=[(0.0, 50.0), (0.25, 30.0), (0.5, 10.0), (0.75, 2.0), (1.0, 0.0)], Camorbit=[(0.0, 100.0), (0.9, 0.0)],
                                       Camdistance=[(0.0, 44.0), (1.0, 16.7)], Camcenter=[(0.0, 1.0), (0.9, 0.0)], Camelevation=[(0.0, 6.0), (1.0, 0.0)], Temporalmode='pointcloud',
                                       Revealfull=[(0.0, 1.0), (0.85, 0.0)], Sourcemix=[(0.0, 0.0), (0.9, 0.6)], Colormode='original', Meshopacity=0.5, Splatopacity=0.6),
         ('hold', float(sp))),
        ('14 REALITY', 14.0, dict(Docmix=[(0.0, 0.0), (0.25, 1.0)], Freezetime=0, Sourcemix=0.0, Timedepth=0.0, Fadeblack=[(0.0, 0.0), (0.9, 0.0), (1.0, 1.0)], Showcontact=0),
         ('run', float(max(0, sp - 30)), 1.0)),
    ]
    ST['scenes'] = SC
    ST['starts'] = np.cumsum([0.0] + [s[1] for s in SC])
    ST['total'] = float(ST['starts'][-1])
    ST['built'] = True


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def setp(name, v):
    p = getattr(C.par, name)
    if hasattr(p, 'menuNames') and p.menuNames:
        p.val = v
    else:
        p.val = float(v)


def track(spec, frac, v0):
    """piecewise smooth interpolation; scalar = ease from the scene-start value over the first 30%"""
    if not isinstance(spec, list):
        if isinstance(spec, str): return spec
        return v0 + (float(spec) - v0) * ease(frac / 0.3)
    pts = [(0.0, v0)] + [(f, float(v)) for f, v in spec if f > 0.0]
    if spec and spec[0][0] <= 0.0: pts[0] = (0.0, float(spec[0][1]))
    for (f0, a), (f1, b) in zip(pts[:-1], pts[1:]):
        if frac <= f1:
            return a + (b - a) * ease((frac - f0) / max(f1 - f0, 1e-6))
    return pts[-1][1]


def step(dt, S):
    if not ST['built']:
        build()
    clock = float(C.par.Showclock.eval()) + dt
    total = ST['total']
    if clock >= total:
        clock -= total
    C.par.Showclock = clock
    sc = int(np.searchsorted(ST['starts'], clock, side='right') - 1)
    sc = min(max(sc, 0), len(ST['scenes']) - 1)
    name, dur, params, play = ST['scenes'][sc]
    tau = clock - ST['starts'][sc]
    frac = tau / dur
    if sc != ST['scene']:
        ST['scene'] = sc
        ST['start_vals'] = {}
        for k in params:
            p = getattr(C.par, k)
            ST['start_vals'][k] = p.val if (hasattr(p, 'menuNames') and p.menuNames) else float(p.eval())
        C.par.Showscene = sc
        # discrete params switch at scene start
        for k, spec in params.items():
            if isinstance(spec, str):
                setp(k, spec)
            elif not isinstance(spec, list) and k in ('Freezetime', 'Showcontact', 'Showshock', 'Showscanplane', 'Samplestep'):
                setp(k, spec)
    for k, spec in params.items():
        if isinstance(spec, str): continue
        if not isinstance(spec, list) and k in ('Freezetime', 'Showcontact', 'Showshock', 'Showscanplane', 'Samplestep'): continue
        v0 = ST['start_vals'].get(k, 0.0)
        if k in ('Freezetime', 'Showcontact', 'Showshock'):
            # list form on a toggle : step at the keyframe
            v = spec[0][1]
            for f, val in spec:
                if frac >= f: v = val
            setp(k, v)
            continue
        setp(k, track(spec, frac, v0))
    # playhead
    kind = play[0]
    last = ST['peaks']['last']
    if kind == 'run':
        if tau < 0.05 or ST.get('run_scene') != sc:
            C.par.Playhead = play[1]
            ST['run_scene'] = sc
        C.par.Playing = 1; C.par.Playspeed = play[2]
        C.par.Freezetime = 0
    elif kind == 'hold':
        C.par.Playing = 0
        C.par.Playhead = play[1]
    elif kind == 'replay':
        C.par.Playing = 0
        a, b, spd = play[1], play[2], play[3]
        ph = a + (tau * FPS_S * spd) % max(b - a, 1.0)
        C.par.Playhead = ph
