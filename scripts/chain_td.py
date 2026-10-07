import json, time
ROOT = 'C:/Users/Utsav/bear-collision'
cfg = json.load(open(ROOT + '/work/chain_cfg.json'))
c = op('/BEAR_COLLISION/CONTROL_PANEL'); rt = c.op('rt').module
c.par.Autoshow = 0; c.par.Playing = 0
tops = cfg['tops']
for ph in cfg['samples']:
    c.par.Playhead = ph
    rt.S['t_last'] = None
    for _ in range(14):
        rt.frame()
        for t in tops: op('/BEAR_COLLISION/' + t).cook(force=True)
        time.sleep(0.12)
    for t in tops:
        op('/BEAR_COLLISION/' + t).save(ROOT + '/work/shots/_c_%d_%s.png' % (ph, t.replace('/', '_')))
result = 'ok'
