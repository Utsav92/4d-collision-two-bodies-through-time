import json, os, time
ROOT = 'C:/Users/Utsav/bear-collision'
cfg = json.load(open(ROOT + '/work/grid_cfg.json'))
c = op('/BEAR_COLLISION/CONTROL_PANEL')
rt = c.op('rt').module
au = op('/BEAR_COLLISION/PERFORMANCE/auto_show').module
au.ST.update({'scene': -1, 'built': False, 'run_scene': None})
au.build()
c.par.Autoshow = 1; c.par.Showclock = 0.0
c.par.Showhud = cfg.get('hud', 0)
rt.S['force_dt'] = cfg.get('dt', 0.5)
c.par.Showhud = cfg.get('hud', 0)
rt.S['t_last'] = None; rt.S['w'] = None
out = op('/BEAR_COLLISION/RENDER/FINAL_OUT')
starts = au.ST['starts']; scenes = au.ST['scenes']
want = [float(starts[i] + scenes[i][1] * cfg.get('k', 0.7)) for i in range(len(scenes))]
only = cfg.get('only')
os.makedirs(ROOT + '/work/shots', exist_ok=True)
names = []
nxt = 0
log = []
while nxt < len(want):
    rt.frame()
    clock = float(c.par.Showclock.eval())
    if clock >= want[nxt]:
        if only is None or nxt in only:
            rr = op('/BEAR_COLLISION/RENDER/render1')
            for _ in range(4):
                rt.frame(); rr.cook(force=True); out.cook(force=True); time.sleep(0.12)
            out.save(ROOT + '/work/shots/scene%02d.png' % (nxt + 1))
            log.append((nxt + 1, round(clock, 1), c.par.Timedepth.eval(), c.par.Camorbit.eval(), c.par.Docmix.eval()))
        nxt += 1
rt.S['force_dt'] = None
c.par.Autoshow = 0
result = str(log)
