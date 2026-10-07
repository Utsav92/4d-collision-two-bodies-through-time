"""usage: python scripts/snap.py name '{"pars":{...}}' -> work/shots/name.png"""
import sys, json, os, subprocess
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
cfg['name'] = sys.argv[1]
json.dump(cfg, open(os.path.join(root, 'work', 'snap_cfg.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(root, 'tdrun.py'), os.path.join(root, 'scripts', 'snap_td.py')], capture_output=True, text=True)
print(r.stdout[-2500:], r.stderr[-1500:])
