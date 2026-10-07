"""MVP5-6: runtime, uniform texture, point-cloud spacetime renderer, camera, render. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
SH = ROOT + '/shaders/'
P = op('/BEAR_COLLISION')
CP = '/BEAR_COLLISION/CONTROL_PANEL'
C = "op('%s').par." % CP
ctrl = P.op('CONTROL_PANEL')
tb = P.op('TEMPORAL_BUFFER')
log = {}


def fresh(parent, typ, name):
    o = parent.op(name)
    if o:
        try: o.destroy()
        except Exception: pass
    return parent.create(typ, name)


def txt(parent, name, text):
    d = fresh(parent, textDAT, name)
    d.text = text
    return d


# ---------------------------------------------------------------- RT page on the control panel
if not [p for p in ctrl.customPages if p.name == 'RT']:
    pg = ctrl.appendCustomPage('RT')
    for n, v in [('Numslices', 40), ('Campx', 0), ('Campy', 0), ('Campz', 16.7), ('Tgtx', 0), ('Tgty', 0), ('Tgtz', 0), ('Projscale', 800)]:
        p = (pg.appendInt(n) if n == 'Numslices' else pg.appendFloat(n))[0]
        p.default = v; p.val = v
        p.min = -1e6; p.max = 1e6; p.normMin = -100; p.normMax = 100
        p.clampMin = False; p.clampMax = False
ctrl.par.Temporalbend = 1.0
ctrl.par.Camdistance = 16.7
ctrl.par.Camfov = 38.0

# ---------------------------------------------------------------- runtime module + frame driver
rt = txt(ctrl, 'rt', open(ROOT + '/scripts/rt_module.py', encoding='utf-8').read())
ex = fresh(ctrl, executeDAT, 'rt_exec')
ex.text = "def onFrameStart(frame):\n    op('%s/rt').module.frame()\n    return\n" % CP
ex.par.framestart = True
ex.par.active = True

# ---------------------------------------------------------------- uniform texture
for o in (tb.op('uni_tex'), tb.op('uni_tex_callbacks')):
    if o:
        try: o.destroy()
        except Exception: pass
u = tb.create(scriptTOP, 'uni_tex')
tb.op('uni_tex_callbacks').text = "def onCook(scriptOp):\n    scriptOp.copyNumpyArray(op('%s/rt').module.UNI)\n" % CP
u.cook(force=True)
log['uni'] = (u.width, u.height)

# ---------------------------------------------------------------- shader DATs
common = open(SH + 'common.glsl').read()
pc = P.op('POINT_CLOUD')
for c in list(pc.children):
    try: c.destroy()
    except Exception: pass
v_pts = txt(pc, 'vs_points', common + '\n' + open(SH + 'points_vs.glsl').read())
f_pts = txt(pc, 'fs_points', open(SH + 'splat_fs.glsl').read())

SAMPLERS = [('sU', 'uni_tex'), ('sP0', 'pts0_tex'), ('sP1', 'pts1_tex'), ('sP2', 'pts2_tex'), ('sInfo', 'info_tex'), ('sPairs', 'pairs_tex'), ('sEv', 'events_tex')]


def make_mat(parent, name, vdat, fdat, additive=True):
    m = fresh(parent, glslMAT, name)
    m.par.vdat = vdat; m.par.pdat = fdat
    for i, (sn, tn) in enumerate(SAMPLERS):
        getattr(m.par, 'sampler%dname' % i).val = sn
        getattr(m.par, 'sampler%dtop' % i).val = tb.op(tn)
    m.par.blending = True
    m.par.srcblend = 'one'; m.par.destblend = 'one'
    m.par.depthtest = False; m.par.depthwriting = False
    return m


def part_geo(parent, name, rows, cols, mat, inst_expr):
    g = fresh(parent, geometryCOMP, name)
    for c in list(g.children):
        try: c.destroy()
        except Exception: pass
    gr = g.create(gridSOP, 'pts'); gr.par.rows = rows; gr.par.cols = cols
    cv = g.create(convertSOP, 'part'); cv.par.totype = 'part'; cv.inputConnectors[0].connect(gr)
    cv.display = True; cv.render = True
    g.par.material = mat
    g.par.instancing = True
    g.par.instancecountmode = 'manual'
    g.par.numinstances.expr = inst_expr
    return g


m_pts = make_mat(pc, 'mat_points', v_pts, f_pts)
g_pts = part_geo(pc, 'geo_points', 32, 48, m_pts, C + 'Numslices')
log['pts_geo'] = (len(g_pts.op('part').points),)

# ---------------------------------------------------------------- camera
cam_c = P.op('CAMERA')
for n in ('cam1', 'cam_target'):
    if cam_c.op(n):
        try: cam_c.op(n).destroy()
        except Exception: pass
tgt = cam_c.create(nullCOMP, 'cam_target')
for a, nm in zip('xyz', ('Tgtx', 'Tgty', 'Tgtz')):
    getattr(tgt.par, 't' + a).expr = C + nm
cam = cam_c.create(cameraCOMP, 'cam1')
for a, nm in zip('xyz', ('Campx', 'Campy', 'Campz')):
    getattr(cam.par, 't' + a).expr = C + nm
cam.par.lookat = tgt
cam.par.fov.expr = C + 'Camfov'
cam.par.near = 0.05; cam.par.far = 800

# ---------------------------------------------------------------- render
rd = P.op('RENDER')
for c in list(rd.children):
    try: c.destroy()
    except Exception: pass
r = rd.create(renderTOP, 'render1')
r.par.camera = cam
r.par.geometry = g_pts.path
r.par.outputresolution = 'custom'; r.par.resolutionw = 1280; r.par.resolutionh = 720
r.par.bgcolorr = 0; r.par.bgcolorg = 0; r.par.bgcolorb = 0
OPQ = '''
out vec4 fragColor;
void main(){ vec4 c = texture(sTD2DInputs[0], vUV.st); fragColor = TDOutputSwizzle(vec4(c.rgb, 1.0)); }
'''
od = txt(rd, 'opaque_glsl', OPQ)
og = rd.create(glslTOP, 'opaque')
og.par.pixeldat = od
og.par.outputresolution = 'custom'; og.par.resolutionw = 1280; og.par.resolutionh = 720
og.inputConnectors[0].connect(r)
o = rd.create(nullTOP, 'OUT_RENDER'); o.inputConnectors[0].connect(og)
log['err'] = {'mat': m_pts.errors(), 'geo': g_pts.errors(), 'render': r.errors()}
log['aa'] = r.par.antialias.menuNames if hasattr(r.par.antialias, 'menuNames') else None
result = {k: str(v) for k, v in log.items()}
