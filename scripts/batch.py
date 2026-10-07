"""usage: python scripts/batch.py gridname  '[{"name":..,"pars":{..}}, ...]'  -> tiles the shots into work/shots/gridname.png (2 columns)"""
import sys, json, os, subprocess
import cv2, numpy as np
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gname = sys.argv[1]
cfgs = json.loads(sys.argv[2])
json.dump(cfgs, open(os.path.join(root, 'work', 'batch_cfg.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(root, 'tdrun.py'), os.path.join(root, 'scripts', 'batch_td.py')], capture_output=True, text=True)
print(r.stdout[-600:], r.stderr[-800:])
ims = []
for c in cfgs:
    im = cv2.imread(os.path.join(root, 'work', 'shots', c['name'] + '.png'))
    ims.append(cv2.putText(cv2.resize(im, (640, 360)), c['name'], (8, 24), 0, 0.7, (0, 255, 255), 2))
if len(ims) % 2: ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + 2]) for i in range(0, len(ims), 2)]
cv2.imwrite(os.path.join(root, 'work', 'shots', gname + '.png'), np.vstack(rows))
