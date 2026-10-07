ROOT = 'C:/Users/Utsav/bear-collision'
ctrl = op('/BEAR_COLLISION/CONTROL_PANEL')
pgs = [pg for pg in ctrl.customPages if pg.name == 'PERFORMANCE']
if pgs and not hasattr(ctrl.par, 'Autoquality'):
    pg = pgs[0]
    p1 = pg.appendToggle('Autoquality', label='AUTO_QUALITY')[0]; p1.default = True; p1.val = True
    p2 = pg.appendFloat('Targetfps', label='TARGET_FPS')[0]; p2.default = 24; p2.val = 24; p2.min = 10; p2.max = 60; p2.normMin = 10; p2.normMax = 60
    p2.clampMin = False; p2.clampMax = False
perf = op('/BEAR_COLLISION/PERFORMANCE')
for c in list(perf.children):
    try: c.destroy()
    except Exception: pass
d = perf.create(textDAT, 'auto_show')
d.text = open(ROOT + '/scripts/auto_show.py', encoding='utf-8').read()
op('/BEAR_COLLISION/CONTROL_PANEL/rt').text = open(ROOT + '/scripts/rt_module.py', encoding='utf-8').read()
m = d.module
result = {'ok': True}
