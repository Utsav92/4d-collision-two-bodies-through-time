"""PARTICLES dust layer + AUDIO live-analysis chain. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
SH = ROOT + '/shaders/'
P = op('/BEAR_COLLISION')
tb = P.op('TEMPORAL_BUFFER')
CP = '/BEAR_COLLISION/CONTROL_PANEL'
C = "op('%s').par." % CP
log = {}


def fresh(parent, typ, name):
    o = parent.op(name)
    if o:
        try: o.destroy()
        except Exception: pass
    return parent.create(typ, name)


pt = P.op('PARTICLES')
for c in list(pt.children):
    try: c.destroy()
    except Exception: pass
common = open(SH + 'common.glsl').read() + '\n' + open(SH + 'slice_fn.glsl').read()
v = pt.create(textDAT, 'vs_dust'); v.text = common + '\n' + open(SH + 'dust_vs.glsl').read()
f = pt.create(textDAT, 'fs_dust'); f.text = open(SH + 'splat_fs.glsl').read()
SAMPLERS = [('sU', 'uni_tex'), ('sP0', 'pts0_tex'), ('sP1', 'pts1_tex'), ('sP2', 'pts2_tex'), ('sInfo', 'info_tex'), ('sPairs', 'pairs_tex'), ('sEv', 'events_tex')]
m = pt.create(glslMAT, 'mat_dust')
m.par.vdat = v; m.par.pdat = f
for i, (sn, tn) in enumerate(SAMPLERS):
    getattr(m.par, 'sampler%dname' % i).val = sn
    getattr(m.par, 'sampler%dtop' % i).val = tb.op(tn)
m.par.blending = True; m.par.srcblend = 'one'; m.par.destblend = 'one'
m.par.depthtest = False; m.par.depthwriting = False
g = pt.create(geometryCOMP, 'geo_dust')
for c in list(g.children):
    try: c.destroy()
    except Exception: pass
gr = g.create(gridSOP, 'pts'); gr.par.rows = 64; gr.par.cols = 64
cv = g.create(convertSOP, 'part'); cv.par.totype = 'part'; cv.inputConnectors[0].connect(gr)
cv.display = True; cv.render = True
g.par.material = m
g.par.instancing = True; g.par.instancecountmode = 'manual'; g.par.numinstances = 6
log['dust_pts'] = len(cv.points)

r = P.op('RENDER/render1')
cur = [x for x in r.par.geometry.eval()]
paths = [x.path for x in cur] if cur and hasattr(cur[0], 'path') else str(r.par.geometry.eval()).split()
if g.path not in paths:
    paths.append(g.path)
r.par.geometry = ' '.join(paths)

# ---------------------------------------------------------------- AUDIO : optional live analysis (video-audio features are precomputed offline)
au = P.op('AUDIO')
for c in list(au.children):
    try: c.destroy()
    except Exception: pass
try:
    ain = au.create(audiodeviceinCHOP, 'audio_in')
    spec = au.create(audiospectrumCHOP, 'audio_spectrum')
    spec.inputConnectors[0].connect(ain)
    out = au.create(nullCHOP, 'OUT_AUDIO_SPECTRUM')
    out.inputConnectors[0].connect(spec)
    log['audio'] = 'chain built'
except Exception as e:
    log['audio'] = 'failed: %s' % e
log['err'] = {'mat': m.errors(), 'geo': g.errors()}
result = {k: str(v) for k, v in log.items()}
