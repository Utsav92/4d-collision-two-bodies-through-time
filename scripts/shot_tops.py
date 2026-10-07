"""usage: python scripts/shot_tops.py name top1 top2 ... (paths relative to /BEAR_COLLISION) -> work/shots/name.png tiled 2 columns"""
import sys, subprocess, os, json
import cv2, numpy as np
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name, tops = sys.argv[1], sys.argv[2:]
code = """
import time
P='/BEAR_COLLISION/'
for p in %s:
    o=op(P+p); o.cook(force=True)
    o.save('C:/Users/Utsav/bear-collision/work/shots/_t_'+p.replace('/','_')+'.png')
""" % json.dumps(tops)
r = subprocess.run([sys.executable, os.path.join(root, 'tdrun.py'), '-c', code], capture_output=True, text=True)
print(r.stdout[-800:], r.stderr[-500:])
ims = []
for p in tops:
    im = cv2.imread(os.path.join(root, 'work', 'shots', '_t_' + p.replace('/', '_') + '.png'))
    ims.append(cv2.resize(im, (640, 360)))
if len(ims) % 2: ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + 2]) for i in range(0, len(ims), 2)]
cv2.imwrite(os.path.join(root, 'work', 'shots', name + '.png'), np.vstack(rows))
