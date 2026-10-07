import time, json
c = op('/BEAR_COLLISION/CONTROL_PANEL')
rt = c.op('rt').module
r = op('/BEAR_COLLISION/RENDER/render1')
P = '/BEAR_COLLISION/'
geos = ['POINT_CLOUD/geo_points', 'CONTACT_FIELD/geo_fibers', 'TEMPORAL_MESH/geo_mesh', 'TEMPORAL_MESH/geo_meshlines', 'SPACETIME_VOLUME/geo_bbox', 'SPACETIME_VOLUME/geo_shock',
        'SPACETIME_VOLUME/geo_scan', 'SPACETIME_VOLUME/geo_video', 'PARTICLES/geo_dust']
allg = ' '.join(P + g for g in geos)
res = {}
rt.frame()
for name in ['ALL'] + geos:
    r.par.geometry = allg if name == 'ALL' else P + name
    for _ in range(2):
        rt.frame(); r.cook(force=True); r.numpyArray()
    t0 = time.perf_counter()
    for _ in range(4):
        rt.frame(); r.cook(force=True); r.numpyArray()
    res[name] = round((time.perf_counter() - t0) / 4 * 1000)
r.par.geometry = allg
result = {'ms': res, 'numslices': int(c.par.Numslices.eval())}
