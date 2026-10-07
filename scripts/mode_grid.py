import subprocess, sys, json, os
import cv2, numpy as np
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
modes = ['fullvolume', 'pointcloud', 'temporalmesh', 'timeslices', 'slitscan', 'contactfield', 'hybrid']
ims = []
for m in modes:
    pars = dict(Playhead=316, Timedepth=30, Camorbit=52, Camelevation=24, Camcenter=1, Camdistance=48, Samplestep=2, Temporalmode=m, Colormode='original')
    pars.update(base)
    pars['Temporalmode'] = m
    cfg = {'top': '/BEAR_COLLISION/RENDER/FINAL_OUT', 'steps': 4, 'pars': pars, 'name': 'mode_' + m}
    json.dump(cfg, open(os.path.join(root, 'work', 'snap_cfg.json'), 'w'))
    r = subprocess.run([sys.executable, os.path.join(root, 'tdrun.py'), os.path.join(root, 'scripts', 'snap_td.py')], capture_output=True, text=True)
    im = cv2.imread(os.path.join(root, 'work', 'shots', 'mode_%s.png' % m))
    ims.append(cv2.putText(cv2.resize(im, (640, 360)), m, (8, 24), 0, 0.8, (0, 255, 255), 2))
ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + 2]) for i in range(0, 8, 2)]
cv2.imwrite(os.path.join(root, 'work', 'shots', 'mode_grid.png'), np.vstack(rows))
