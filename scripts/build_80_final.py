"""1080p output path + misc finishing. Idempotent."""
P = op('/BEAR_COLLISION')
ctrl = P.op('CONTROL_PANEL')
CP = "op('/BEAR_COLLISION/CONTROL_PANEL').par."
pg = [p for p in ctrl.customPages if p.name == 'PERFORMANCE'][0]
if not hasattr(ctrl.par, 'Outres'):
    m = pg.appendMenu('Outres', label='OUTPUT_RES')[0]
    m.menuNames = ['hd720', 'hd1080']; m.menuLabels = ['1280 x 720 (working)', '1920 x 1080 (final render path)']
    m.default = 'hd720'; m.val = 'hd720'
W = "(1920 if %sOutres.eval() == 'hd1080' else 1280) + 0*absTime.frame" % CP
H = "(1080 if %sOutres.eval() == 'hd1080' else 720) + 0*absTime.frame" % CP
log = []
for path in ['RENDER/render1', 'RENDER/opaque', 'POST_FX/add_bloom', 'POST_FX/final_pass', 'POST_FX/hud_text']:
    o = P.op(path)
    o.par.resolutionw.expr = W
    o.par.resolutionh.expr = H
    log.append((path, o.width, o.height))
ctrl.par.Showhud = 1
result = str(log)
