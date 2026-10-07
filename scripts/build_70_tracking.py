tr = op('/BEAR_COLLISION/BEAR_TRACKING')
NAMES = ['bearA_x', 'bearA_y', 'bearB_x', 'bearB_y', 'bear_distance', 'bearA_velocity', 'bearB_velocity', 'relative_velocity', 'interaction_intensity',
         'gap', 'contact', 'bearA_vx', 'bearA_vy', 'bearB_vx', 'bearB_vy', 'bboxA_x0', 'bboxA_y0', 'bboxA_x1', 'bboxA_y1', 'bboxB_x0', 'bboxB_y0', 'bboxB_x1', 'bboxB_y1']
for n in ('OUT_TRACKING',):
    if tr.op(n): tr.op(n).destroy()
ct = tr.create(constantCHOP, 'OUT_TRACKING')
for i, n in enumerate(NAMES):
    getattr(ct.par, 'name%d' % i).val = n
    getattr(ct.par, 'value%d' % i).val = 0.0
for who in ('A', 'B'):
    comp = tr.op('BEAR_' + who)
    for c in list(comp.children):
        try: c.destroy()
        except Exception: pass
    s = comp.create(selectCHOP, 'sel')
    s.par.chops = ct.path
    s.par.channames = 'bear%s_* bbox%s_*' % (who, who)
    n = comp.create(nullCHOP, 'BEAR_%s_TRACK' % who); n.inputConnectors[0].connect(s)
result = {'chans': ct.numChans}
