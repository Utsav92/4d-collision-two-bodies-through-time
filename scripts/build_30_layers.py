"""MVP9-13 layers: contact fibres, temporal mesh, shockwaves, slice frames, scan plane, video plane. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
SH = ROOT + '/shaders/'
P = op('/BEAR_COLLISION')
CP = '/BEAR_COLLISION/CONTROL_PANEL'
C = "op('%s').par." % CP
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


def clear(comp):
    for c in list(comp.children):
        try: c.destroy()
        except Exception: pass


common = open(SH + 'common.glsl').read() + '\n' + open(SH + 'slice_fn.glsl').read()
LINES_FS = open(SH + 'lines_fs.glsl').read()
SAMPLERS = [('sU', 'uni_tex'), ('sP0', 'pts0_tex'), ('sP1', 'pts1_tex'), ('sP2', 'pts2_tex'), ('sInfo', 'info_tex'), ('sPairs', 'pairs_tex'), ('sEv', 'events_tex')]


def make_mat(parent, name, vdat, fdat, extra=None):
    m = fresh(parent, glslMAT, name)
    m.par.vdat = vdat; m.par.pdat = fdat
    for i, (sn, tn) in enumerate(SAMPLERS):
        getattr(m.par, 'sampler%dname' % i).val = sn
        getattr(m.par, 'sampler%dtop' % i).val = tb.op(tn)
    if extra:
        extra(m)
    m.par.blending = True
    m.par.srcblend = 'one'; m.par.destblend = 'one'
    m.par.depthtest = False; m.par.depthwriting = False
    return m


def poly_geo(parent, name, npolys, nverts, mat, inst_expr, closed=False):
    g = fresh(parent, geometryCOMP, name)
    clear(g)
    s = g.create(scriptSOP, 'prims')
    g.op('prims_callbacks').text = '''
def onCook(scriptOp):
    scriptOp.clear()
    for i in range(%d):
        scriptOp.appendPoly(%d, closed=False, addPoints=True)
''' % (npolys, nverts)
    s.cook(force=True)
    s.display = True; s.render = True
    g.par.material = mat
    if inst_expr:
        g.par.instancing = True
        g.par.instancecountmode = 'manual'
        g.par.numinstances.expr = inst_expr
    log[name] = (len(s.points), len(s.prims))
    return g


NS = C + 'Numslices'

# ---------------------------------------------------------------- CONTACT_FIELD
cf = P.op('CONTACT_FIELD'); clear(cf)
v = txt(cf, 'vs_fibers', common + '\n' + open(SH + 'fibers_vs.glsl').read())
f = txt(cf, 'fs_lines', LINES_FS)
m_fib = make_mat(cf, 'mat_fibers', v, f)
g_fib = poly_geo(cf, 'geo_fibers', 192 * 10, 2, m_fib, NS)

# ---------------------------------------------------------------- TEMPORAL_MESH
tm = P.op('TEMPORAL_MESH'); clear(tm)
v1 = txt(tm, 'vs_mesh', common + '\n' + open(SH + 'mesh_vs.glsl').read())
v2 = txt(tm, 'vs_meshlines', common + '\n' + open(SH + 'meshlines_vs.glsl').read())
f2 = txt(tm, 'fs_lines', LINES_FS)
m_mesh = make_mat(tm, 'mat_mesh', v1, f2)
m_ml = make_mat(tm, 'mat_meshlines', v2, f2)
g_mesh = poly_geo(tm, 'geo_mesh', 512, 3, m_mesh, NS)
g_ml = poly_geo(tm, 'geo_meshlines', 512, 2, m_ml, NS)

# ---------------------------------------------------------------- SPACETIME_VOLUME : slice frames, shockwaves, scan plane, video plane
sv = P.op('SPACETIME_VOLUME'); clear(sv)
v3 = txt(sv, 'vs_bbox', common + '\n' + open(SH + 'bbox_vs.glsl').read())
v4 = txt(sv, 'vs_shock', common + '\n' + open(SH + 'shock_vs.glsl').read())
v5 = txt(sv, 'vs_plane', common + '\n' + open(SH + 'plane_vs.glsl').read())
f5 = txt(sv, 'fs_plane', open(SH + 'plane_fs.glsl').read())
f3 = txt(sv, 'fs_lines', LINES_FS)
m_bb = make_mat(sv, 'mat_bbox', v3, f3)
m_sh = make_mat(sv, 'mat_shock', v4, f3)
g_bb = poly_geo(sv, 'geo_bbox', 8, 2, m_bb, NS)
g_sh = poly_geo(sv, 'geo_shock', 96, 2, m_sh, '48')


def plane_extra(kind):
    def fn(m):
        m.par.vec0name = 'uPlane'
        m.par.vec0valuex = 1.0 if kind == 'video' else 0.0
        m.par.vec0valuey.expr = C + ('Sourcemix' if kind == 'video' else 'Showscanplane')
        m.par.vec0valuez = 0; m.par.vec0valuew = 0
        if kind == 'video':
            m.par.sampler7name = 'sSrc'
            m.par.sampler7top = op('/BEAR_COLLISION/SOURCE/SOURCE_VIDEO')
    return fn


def plane_geo(name, mat):
    g = fresh(sv, geometryCOMP, name)
    clear(g)
    gr = g.create(gridSOP, 'plane'); gr.par.rows = 2; gr.par.cols = 2
    gr.par.sizex = 1; gr.par.sizey = 1
    gr.display = True; gr.render = True
    g.par.material = mat
    return g


m_scan = make_mat(sv, 'mat_scan', v5, f5, plane_extra('scan'))
m_vid = make_mat(sv, 'mat_video', v5, f5, plane_extra('video'))
g_scan = plane_geo('geo_scan', m_scan)
g_vid = plane_geo('geo_video', m_vid)
log['plane_pts'] = len(g_scan.op('plane').points)

# ---------------------------------------------------------------- render: all geometry
r = P.op('RENDER/render1')
geos = ['POINT_CLOUD/geo_points', 'CONTACT_FIELD/geo_fibers', 'TEMPORAL_MESH/geo_mesh', 'TEMPORAL_MESH/geo_meshlines',
        'SPACETIME_VOLUME/geo_bbox', 'SPACETIME_VOLUME/geo_shock', 'SPACETIME_VOLUME/geo_scan', 'SPACETIME_VOLUME/geo_video']
r.par.geometry = ' '.join(P.op(g).path for g in geos)
errs = {}
for comp in ('CONTACT_FIELD', 'TEMPORAL_MESH', 'SPACETIME_VOLUME'):
    for o in P.op(comp).children:
        e = o.errors() + o.warnings()
        if e: errs[comp + '/' + o.name] = e[:300]
log['errs'] = errs
result = {k: str(v) for k, v in log.items()}
