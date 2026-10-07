import json, os
ROOT = 'C:/Users/Utsav/bear-collision'
cfg = json.load(open(ROOT + '/work/snap_cfg.json'))
c = op('/BEAR_COLLISION/CONTROL_PANEL')
rt = c.op('rt').module
c.par.Autoshow = 0
c.par.Playing = 0
BASE = dict(Docmix=0, Fadeblack=0, Freezetime=0, Explode=0, Dissolve=0, Revealfull=0, Showhud=0, Showcontact=1, Showshock=1, Showscanplane=1, Sourcemix=0,
            Bearseparation=0, Collisionstrength=1, Turbulence=0, Noiseamount=0, Temporalcurl=0, Temporalbend=1, Scanspeed=0)
for k, v in BASE.items():
    getattr(c.par, k).val = v
for k, v in cfg.get('pars', {}).items():
    getattr(c.par, k).val = v
rt.S['t_last'] = None
rt.S['w'] = None
import time
out = op(cfg.get('top', '/BEAR_COLLISION/RENDER/OUT_RENDER'))
for i in range(cfg.get('steps', 3)):
    rt.frame()
    out.cook(force=True)
    time.sleep(0.15)
out.cook(force=True)
os.makedirs(ROOT + '/work/shots', exist_ok=True)
out.save(ROOT + '/work/shots/%s.png' % cfg.get('name', 'snap'))
errs = {}
for path in cfg.get('chk', ['/BEAR_COLLISION/POINT_CLOUD']):
    for o in op(path).children:
        e = o.errors() + o.warnings()
        if e: errs[o.name] = e[:500]
r = op('/BEAR_COLLISION/RENDER/render1')
result = {'errs': errs, 'cook_ms': round(r.cookTime * 1000, 1), 'numslices': int(c.par.Numslices.eval()), 'render_err': r.errors(), 'U0': [round(float(x), 3) for x in rt.UNI[0][0]]}
