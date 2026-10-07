"""MVP2-4: TEMPORAL_BUFFER data textures, SEGMENTATION / BACKGROUND_REMOVAL chains, TRACKING CHOPs. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
P = op('/BEAR_COLLISION')
CP = "op('/BEAR_COLLISION/CONTROL_PANEL').par."
log = {}


def fresh(parent, typ, name):
    o = parent.op(name)
    if o: o.destroy()
    return parent.create(typ, name)


def txt(parent, name, text):
    d = fresh(parent, textDAT, name)
    d.text = text
    return d


# ---------------------------------------------------------------- TEMPORAL_BUFFER : float textures
tb = P.op('TEMPORAL_BUFFER')
LOAD = '''
import numpy as np
def onCook(scriptOp):
    a = np.load(r"%s/data/%s.npy").astype(np.float32)
    if a.ndim == 2: a = a[None]
    scriptOp.copyNumpyArray(a)
'''
for nm, f in [('pts0_tex', 'pts0'), ('pts1_tex', 'pts1'), ('pts2_tex', 'pts2'), ('info_tex', 'info'), ('pairs_tex', 'pairs'), ('events_tex', 'events')]:
    for o in (tb.op(nm), tb.op(nm + '_callbacks')):
        if o: o.destroy()
    s = tb.create(scriptTOP, nm)
    tb.op(nm + '_callbacks').text = LOAD % (ROOT, f)
    s.cook(force=True)
    log[nm] = (s.width, s.height)


def movie(parent, name, file, idx_expr):
    m = fresh(parent, moviefileinTOP, name)
    m.par.file = ROOT + '/data/' + file
    m.par.play = False
    m.par.playmode = 'specify'
    m.par.playmode = 'specify'
    m.par.index.expr = idx_expr
    m.par.reloadpulse.pulse()
    return m


IDX = "int(" + CP + "Playhead.eval())"
mask_in = movie(tb, 'mask_video', 'mask.mp4', IDX)
depth_in = movie(tb, 'depth_video', 'depth.mp4', IDX)
flow_in = movie(tb, 'flow_video', 'flow.mp4', IDX)

# ---------------------------------------------------------------- BACKGROUND_REMOVAL + BEAR_SEGMENTATION
seg = P.op('BEAR_SEGMENTATION')
bg = P.op('BACKGROUND_REMOVAL')
for c in list(seg.children) + list(bg.children):
    try: c.destroy()
    except Exception: pass


def sel(parent, name, top):
    s = parent.create(selectTOP, name)
    s.par.top = top.path
    return s


FIT = '''
vec2 res = vec2(textureSize(sTD2DInputs[0], 0));
'''
s_mask = sel(seg, 'sel_mask_video', mask_in)
fit = seg.create(fitTOP, 'mask_fit720')
fit.par.outputresolution = 'custom'; fit.par.resolutionw = 1280; fit.par.resolutionh = 720
fit.inputConnectors[0].connect(s_mask)

MORPH = '''
uniform vec4 uM; // x = erode radius px, y = dilate radius px
out vec4 fragColor;
void main(){
    vec2 px = 1.0 / vec2(textureSize(sTD2DInputs[0], 0));
    vec4 c = texture(sTD2DInputs[0], vUV.st);
    int re = int(uM.x + 0.5), rd = int(uM.y + 0.5);
    vec4 mn = c, mx = c;
    int r = max(re, rd);
    for (int j = -8; j <= 8; j++) for (int i = -8; i <= 8; i++) {
        if (abs(i) > r || abs(j) > r) continue;
        vec4 s = texture(sTD2DInputs[0], vUV.st + vec2(i, j) * px);
        if (abs(i) <= re && abs(j) <= re) mn = min(mn, s);
        if (abs(i) <= rd && abs(j) <= rd) mx = max(mx, s);
    }
    vec4 o = c;
    if (re > 0) o = mn;
    if (rd > 0) o = max(o, mx);
    fragColor = TDOutputSwizzle(o);
}
'''
morph_dat = txt(seg, 'morph_glsl', MORPH)
morph = seg.create(glslTOP, 'mask_morph')
morph.par.pixeldat = morph_dat
morph.par.outputresolution = 'custom'; morph.par.resolutionw = 1280; morph.par.resolutionh = 720
morph.inputConnectors[0].connect(fit)
morph.par.vec0name = 'uM'
morph.par.vec0valuex.expr = CP + 'Erode'
morph.par.vec0valuey.expr = CP + 'Dilate'
morph.par.vec0valuez = 0; morph.par.vec0valuew = 0

blur = seg.create(blurTOP, 'mask_feather')
blur.par.size.expr = CP + 'Maskfeather'
blur.inputConnectors[0].connect(morph)

CLEAN = '''
uniform vec4 uC; // x thr, y feather(soft width), z edge cleanup, w unused
out vec4 fragColor;
void main(){
    vec4 m = texture(sTD2DInputs[0], vUV.st);
    float w = max(uC.y, 0.002);
    // edge cleanup: a wider soft version removes thin stray speckles
    vec2 px = 1.0 / vec2(textureSize(sTD2DInputs[0], 0));
    vec4 a = vec4(0.0);
    for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) a += texture(sTD2DInputs[0], vUV.st + vec2(i, j) * px * 2.0);
    a /= 25.0;
    vec4 mm = mix(m, min(m, a * 1.6), uC.z);
    vec4 o = smoothstep(uC.x - w, uC.x + w, mm);
    fragColor = TDOutputSwizzle(vec4(o.rgb, 1.0));
}
'''
clean_dat = txt(seg, 'clean_glsl', CLEAN)
clean = seg.create(glslTOP, 'mask_clean')
clean.par.pixeldat = clean_dat
clean.par.outputresolution = 'custom'; clean.par.resolutionw = 1280; clean.par.resolutionh = 720
clean.inputConnectors[0].connect(blur)
clean.par.vec0name = 'uC'
clean.par.vec0valuex.expr = CP + 'Maskthreshold'
clean.par.vec0valuey = 0.12
clean.par.vec0valuez.expr = CP + 'Edgecleanup'
clean.par.vec0valuew = 0
out_masks = seg.create(nullTOP, 'OUT_BEAR_MASKS_ABU')      # R = bear A, G = bear B, B = union
out_masks.inputConnectors[0].connect(clean)

ONE = '''
out vec4 fragColor;
void main(){ vec4 m = texture(sTD2DInputs[0], vUV.st); fragColor = TDOutputSwizzle(vec4(vec3(%s), 1.0)); }
'''
for nm, ch in [('OUT_BEAR_MASK', 'm.b'), ('OUT_BEAR_A_MASK', 'm.r'), ('OUT_BEAR_B_MASK', 'm.g')]:
    d = txt(seg, nm.lower() + '_glsl', ONE % ch)
    g = seg.create(glslTOP, nm.lower() + '_pass')
    g.par.pixeldat = d
    g.par.outputresolution = 'custom'; g.par.resolutionw = 1280; g.par.resolutionh = 720
    g.inputConnectors[0].connect(out_masks)
    n = seg.create(nullTOP, nm)
    n.inputConnectors[0].connect(g)

# bear-only RGB : source x mask, background suppression
src_sel = sel(bg, 'sel_source', op('/BEAR_COLLISION/SOURCE/SOURCE_VIDEO'))
mask_sel = sel(bg, 'sel_mask', seg.op('OUT_BEAR_MASK'))
RGB = '''
uniform vec4 uB; // x = background suppression
out vec4 fragColor;
void main(){
    vec4 s = texture(sTD2DInputs[0], vUV.st);
    float m = texture(sTD2DInputs[1], vUV.st).r;
    vec3 c = mix(s.rgb, s.rgb * m, uB.x);
    fragColor = TDOutputSwizzle(vec4(c, m));
}
'''
rgb_dat = txt(bg, 'bear_rgb_glsl', RGB)
rgbg = bg.create(glslTOP, 'bear_rgb_pass')
rgbg.par.pixeldat = rgb_dat
rgbg.par.outputresolution = 'custom'; rgbg.par.resolutionw = 1280; rgbg.par.resolutionh = 720
rgbg.inputConnectors[0].connect(src_sel); rgbg.inputConnectors[1].connect(mask_sel)
rgbg.par.vec0name = 'uB'
rgbg.par.vec0valuex.expr = CP + 'Backgroundsuppression'
for a in 'yzw': getattr(rgbg.par, 'vec0value' + a).val = 0
o1 = bg.create(nullTOP, 'OUT_BEAR_RGB'); o1.inputConnectors[0].connect(rgbg)

# background with bears removed: normalised blur of the unmasked pixels, so the bears are filled from their surroundings
NUM = '''
out vec4 fragColor;
void main(){
    vec4 s = texture(sTD2DInputs[0], vUV.st);
    float m = texture(sTD2DInputs[1], vUV.st).r;
    float keep = 1.0 - clamp(m * 1.4, 0.0, 1.0);
    fragColor = TDOutputSwizzle(vec4(s.rgb * keep, keep));
}
'''
num_dat = txt(bg, 'bg_num_glsl', NUM)
numg = bg.create(glslTOP, 'bg_num')
numg.par.pixeldat = num_dat
numg.par.outputresolution = 'custom'; numg.par.resolutionw = 1280; numg.par.resolutionh = 720
numg.inputConnectors[0].connect(src_sel); numg.inputConnectors[1].connect(mask_sel)
bl = bg.create(blurTOP, 'bg_blur'); bl.par.size = 50; bl.par.extend = 'mirror'
bl.inputConnectors[0].connect(numg)
bl2 = bg.create(blurTOP, 'bg_blur_wide'); bl2.par.size = 600; bl2.par.extend = 'mirror'
bl2.inputConnectors[0].connect(numg)
PREP = '''
out vec4 fragColor;
void main(){
    vec4 b = texture(sTD2DInputs[0], vUV.st);
    vec4 w = texture(sTD2DInputs[1], vUV.st);
    vec3 fn = b.rgb / max(b.a, 0.02);
    vec3 fw = w.a > 0.004 ? w.rgb / w.a : vec3(0.30, 0.36, 0.28);
    fragColor = TDOutputSwizzle(vec4(mix(fw, fn, smoothstep(0.03, 0.25, b.a)), 1.0));
}
'''
prep_dat = txt(bg, 'bg_prep_glsl', PREP)
prep = bg.create(glslTOP, 'bg_prep')
prep.par.pixeldat = prep_dat
prep.par.outputresolution = 'custom'; prep.par.resolutionw = 1280; prep.par.resolutionh = 720
prep.inputConnectors[0].connect(bl); prep.inputConnectors[1].connect(bl2)
FILL = '''
out vec4 fragColor;
void main(){
    vec4 s = texture(sTD2DInputs[0], vUV.st);
    float m = clamp(texture(sTD2DInputs[1], vUV.st).r * 1.4, 0.0, 1.0);
    vec3 fill = texture(sTD2DInputs[2], vUV.st).rgb;
    fragColor = TDOutputSwizzle(vec4(mix(s.rgb, fill, m), 1.0));
}
'''
fill_dat = txt(bg, 'bg_fill_glsl', FILL)
fillg = bg.create(glslTOP, 'bg_fill')
fillg.par.pixeldat = fill_dat
fillg.par.outputresolution = 'custom'; fillg.par.resolutionw = 1280; fillg.par.resolutionh = 720
fillg.inputConnectors[0].connect(src_sel); fillg.inputConnectors[1].connect(mask_sel); fillg.inputConnectors[2].connect(prep)
o2 = bg.create(nullTOP, 'OUT_BACKGROUND'); o2.inputConnectors[0].connect(fillg)

# ---------------------------------------------------------------- DEPTH / OPTICAL_FLOW viewers
for comp, nm, m in [(P.op('DEPTH'), 'OUT_DEPTH', depth_in), (P.op('OPTICAL_FLOW'), 'OUT_FLOW', flow_in)]:
    for c in list(comp.children):
        try: c.destroy()
        except Exception: pass
    s = sel(comp, 'sel_' + nm.lower(), m)
    f = comp.create(fitTOP, nm.lower() + '_fit')
    f.par.outputresolution = 'custom'; f.par.resolutionw = 1280; f.par.resolutionh = 720
    f.inputConnectors[0].connect(s)
    n = comp.create(nullTOP, nm); n.inputConnectors[0].connect(f)

# ---------------------------------------------------------------- BEAR_TRACKING : CHOPs from tracking.csv
tr = P.op('BEAR_TRACKING')
for o in list(tr.children):
    if o.name not in ('BEAR_A', 'BEAR_B'):
        try: o.destroy()
        except Exception: pass
tt = tr.create(tableDAT, 'tracking_table')
tt.par.file = ROOT + '/data/tracking.csv'
tt.par.loadonstart = True
tt.par.loadonstartpulse.pulse() if hasattr(tt.par, 'loadonstartpulse') else None
log['table'] = (tt.numRows, tt.numCols)
d2c = tr.create(dattoCHOP, 'tracking_chop')
d2c.par.dat = tt
log['d2c_pars'] = [p.name for p in d2c.pars()]
result = {k: str(v) for k, v in log.items()}
