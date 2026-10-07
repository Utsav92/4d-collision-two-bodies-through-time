import json, os, time
ROOT = 'C:/Users/Utsav/bear-collision'
cfgs = json.load(open(ROOT + '/work/batch_cfg.json'))
c = op('/BEAR_COLLISION/CONTROL_PANEL')
rt = c.op('rt').module
r = op('/BEAR_COLLISION/RENDER/render1')
BASE = dict(Docmix=0, Fadeblack=0, Freezetime=0, Explode=0, Dissolve=0, Revealfull=0, Showhud=0, Showcontact=1, Showshock=1, Showscanplane=1, Sourcemix=0,
            Bearseparation=0, Collisionstrength=1, Turbulence=0, Noiseamount=0, Temporalcurl=0, Temporalbend=1, Scanspeed=0, Timegeometry='linear', Autoshow=0, Playing=0)
res = []
for cfg in cfgs:
    for k, v in BASE.items():
        getattr(c.par, k).val = v
    for k, v in cfg['pars'].items():
        getattr(c.par, k).val = v
    out = op(cfg.get('top', '/BEAR_COLLISION/RENDER/FINAL_OUT'))
    rt.S['t_last'] = None; rt.S['w'] = None
    for _ in range(cfg.get('steps', 3)):
        rt.frame(); r.cook(force=True); out.cook(force=True)
    r.cook(force=True); out.cook(force=True)
    out.save(ROOT + '/work/shots/%s.png' % cfg['name'])
    res.append((cfg['name'], int(c.par.Numslices.eval())))
result = str(res)
