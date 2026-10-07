"""Stage A (offline CV) for 4D COLLISION. Resumable.
Per sample (every STEP-th video frame) caches work/cache/frame_XXX.npz:
  instance masks (Mask R-CNN, animal classes), boxes, scores, labels
  monocular depth (Depth Anything V2 small), half-res
  Farneback flow vs previous sample (half-res), camera motion similarity A_t (frame t -> t-1, half-res px)
usage: python cv_stage_a.py [limit]
"""
import os, sys, time, json
import numpy as np, cv2, torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO = r'C:\Users\Utsav\Downloads\07.10.2026_03.14.43_REC.mp4'
CACHE = os.path.join(ROOT, 'work', 'cache')
os.makedirs(CACHE, exist_ok=True)

STEP = 2
CROP = (0, 574, 0, 1150)          # y0,y1,x0,x1 : drops the recorder pop-up strip on the right edge
LOW_W = 575                        # flow / camera / depth width (half of crop)
ANIMAL_LABELS = set(range(16, 26))
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9

torch.set_num_threads(os.cpu_count() or 4)


def read_frames():
    cap = cv2.VideoCapture(VIDEO)
    out, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % STEP == 0:
            y0, y1, x0, x1 = CROP
            out.append(f[y0:y1, x0:x1].copy())
        i += 1
    return out


def main():
    t0 = time.time()
    frames = read_frames()[:LIMIT]
    n = len(frames)
    H, W = frames[0].shape[:2]
    lh = int(round(H * LOW_W / W))
    print('samples', n, 'crop', H, W, 'low', lh, LOW_W, flush=True)

    from torchvision.models.detection import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
    det = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT, box_score_thresh=0.2,
                                min_size=640, max_size=1280).eval()
    from transformers import pipeline
    from PIL import Image
    dep = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf')

    lows = [cv2.cvtColor(cv2.resize(f, (LOW_W, lh), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for f in frames]
    cam = np.zeros((n, 2, 3), np.float32)
    cam[:, 0, 0] = 1; cam[:, 1, 1] = 1
    cam_conf = np.ones(n, np.float32)
    cpath = os.path.join(CACHE, 'camera.npy')
    if os.path.exists(cpath):
        cam = np.load(cpath); cam_conf = np.load(os.path.join(CACHE, 'camera_conf.npy'))
        if len(cam) != n:
            cam = np.zeros((n, 2, 3), np.float32); cam[:, 0, 0] = 1; cam[:, 1, 1] = 1; cam_conf = np.ones(n, np.float32)

    for t in range(n):
        fn = os.path.join(CACHE, 'frame_%03d.npz' % t)
        if os.path.exists(fn):
            continue
        ts = time.time()
        rgb = cv2.cvtColor(frames[t], cv2.COLOR_BGR2RGB)
        with torch.no_grad():
            x = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
            o = det([x])[0]
        keep = [k for k in range(len(o['scores'])) if int(o['labels'][k]) in ANIMAL_LABELS and float(o['scores'][k]) >= 0.25]
        boxes = o['boxes'][keep].numpy().astype(np.float32) if keep else np.zeros((0, 4), np.float32)
        labels = o['labels'][keep].numpy().astype(np.int16) if keep else np.zeros(0, np.int16)
        scores = o['scores'][keep].numpy().astype(np.float32) if keep else np.zeros(0, np.float32)
        masks = (o['masks'][keep, 0].numpy() > 0.5) if keep else np.zeros((0, H, W), bool)

        d = dep(Image.fromarray(rgb))['predicted_depth']
        d = torch.nn.functional.interpolate(d[None] if d.ndim == 3 else d[None, None], size=(lh, LOW_W), mode='bilinear')[0, 0].numpy()
        depth = d.astype(np.float16)

        flow = np.zeros((lh, LOW_W, 2), np.float16)
        if t > 0:
            prev, cur = lows[t - 1], lows[t]
            m = np.full(cur.shape, 255, np.uint8)
            for mk in masks:
                mm = cv2.resize(mk.astype(np.uint8), (LOW_W, lh), interpolation=cv2.INTER_NEAREST)
                m[cv2.dilate(mm, np.ones((13, 13), np.uint8)) > 0] = 0
            pts = cv2.goodFeaturesToTrack(cur, 500, 0.01, 6, mask=m)
            A = np.array([[1, 0, 0], [0, 1, 0]], np.float32)
            conf = 0.0
            if pts is not None and len(pts) > 12:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(cur, prev, pts, None, winSize=(21, 21), maxLevel=3)
                good = st[:, 0] == 1
                if good.sum() > 12:
                    M, inl = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                    if M is not None:
                        A = M.astype(np.float32); conf = float(inl.sum()) / max(1, good.sum())
            cam[t] = A; cam_conf[t] = conf
            flow = cv2.calcOpticalFlowFarneback(prev, cur, None, 0.5, 3, 15, 3, 5, 1.2, 0).astype(np.float16)

        np.savez_compressed(fn, boxes=boxes, labels=labels, scores=scores,
                            masks=np.packbits(masks, axis=-1) if len(masks) else np.zeros((0, H, 1), np.uint8),
                            depth=depth, flow=flow)
        np.save(cpath, cam); np.save(os.path.join(CACHE, 'camera_conf.npy'), cam_conf)
        print('t=%03d dets=%d labels=%s scores=%s %.1fs (elapsed %.0fs)' % (t, len(keep), labels.tolist(), np.round(scores, 2).tolist(), time.time() - ts, time.time() - t0), flush=True)

    json.dump({'n': n, 'H': H, 'W': W, 'lh': lh, 'LOW_W': LOW_W, 'STEP': STEP, 'CROP': CROP}, open(os.path.join(CACHE, 'meta.json'), 'w'))
    print('DONE', time.time() - t0, flush=True)


if __name__ == '__main__':
    main()
