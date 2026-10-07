ROOT = 'C:/Users/Utsav/bear-collision'
d = op('/BEAR_COLLISION/CONTROL_PANEL/rt')
d.text = open(ROOT + '/scripts/rt_module.py', encoding='utf-8').read()
m = d.module
m.S['t_last'] = None
result = 'rt pushed, S keys: %d' % len(m.S)
