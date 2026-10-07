import subprocess, sys, json, os
import cv2, numpy as np
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
json.dump(cfg, open(os.path.join(root, 'work', 'grid_cfg.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(root, 'tdrun.py'), os.path.join(root, 'scripts', 'show_grid_td.py')], capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-1500:])
ims = []
for i in range(1, 15):
    f = os.path.join(root, 'work', 'shots', 'scene%02d.png' % i)
    im = cv2.imread(f) if os.path.exists(f) else np.zeros((720, 1280, 3), np.uint8)
    ims.append(cv2.putText(cv2.resize(im, (480, 270)), str(i), (8, 24), 0, 0.8, (0, 255, 255), 2))
ims += [np.zeros_like(ims[0])]
rows = [np.hstack(ims[i:i + 3]) for i in range(0, 15, 3)]
cv2.imwrite(os.path.join(root, 'work', 'shots', 'show_grid.png'), np.vstack(rows))
