import time
c = op('/BEAR_COLLISION/CONTROL_PANEL')
rt = c.op('rt').module
r = op('/BEAR_COLLISION/RENDER/render1')
c.par.Autoshow = 0; c.par.Playing = 0
for k, v in dict(Playhead=316, Timedepth=30, Camorbit=52, Camelevation=24, Camcenter=1, Camdistance=48, Samplestep=2, Docmix=0, Freezetime=0, Revealfull=0).items():
    getattr(c.par, k).val = v
out = []
for m in ['pointcloud', 'temporalmesh', 'timeslices', 'contactfield']:
    c.par.Temporalmode = m
    rt.S['t_last'] = None; rt.S['w'] = None
    for _ in range(3):
        rt.frame(); r.cook(force=True)
    o_ = op('/BEAR_COLLISION/RENDER/FINAL_OUT'); o_.cook(force=True); o_.save('C:/Users/Utsav/bear-collision/work/shots/dbg_%s.png' % m)
    a = r.numpyArray()
    out.append((m, round(float(a[..., :3].mean()), 5), [round(float(x), 2) for x in rt.UNI[0][18]], [round(float(x), 2) for x in rt.UNI[0][4]]))
result = out
