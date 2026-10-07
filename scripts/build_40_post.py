"""POST_FX + final output + HUD. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
P = op('/BEAR_COLLISION')
ctrl = P.op('CONTROL_PANEL')
CP = '/BEAR_COLLISION/CONTROL_PANEL'
C = "op('%s').par." % CP
log = {}

if not [p for p in ctrl.customPages if p.name == 'POST']:
    pg = ctrl.appendCustomPage('POST')
    for n, lab, v, lo, hi in [('Exposure', 'EXPOSURE', 1.15, 0.2, 4), ('Bloomamount', 'BLOOM', 0.65, 0, 3), ('Bloomsize', 'BLOOM_SIZE', 18, 1, 60),
                              ('Vignette', 'VIGNETTE', 0.55, 0, 1.5), ('Grain', 'GRAIN', 0.035, 0, 0.3), ('Chroma', 'CHROMA', 0.0015, 0, 0.02),
                              ('Fadeblack', 'FADE_TO_BLACK', 0.0, 0, 1), ('Docmix', 'DOCUMENTARY_MIX', 0.0, 0, 1)]:
        p = pg.appendFloat(n, label=lab)[0]
        p.default = v; p.val = v; p.min = lo; p.max = hi; p.normMin = lo; p.normMax = hi
        p.clampMin = False; p.clampMax = False

pf = P.op('POST_FX')
for c in list(pf.children):
    try: c.destroy()
    except Exception: pass


def txt(parent, name, text):
    d = parent.create(textDAT, name)
    d.text = text
    return d


def sel(name, path):
    s = pf.create(selectTOP, name)
    s.par.top = path
    return s


rend = sel('sel_render', '/BEAR_COLLISION/RENDER/OUT_RENDER')
srcv = sel('sel_source', '/BEAR_COLLISION/SOURCE/SOURCE_VIDEO')

# bloom : bright pass -> blur
BRIGHT = '''
out vec4 fragColor;
void main(){
    vec3 c = texture(sTD2DInputs[0], vUV.st).rgb;
    float l = dot(c, vec3(0.299, 0.587, 0.114));
    fragColor = TDOutputSwizzle(vec4(c * smoothstep(0.35, 1.1, l), 1.0));
}
'''
bd = txt(pf, 'bright_glsl', BRIGHT)
bp = pf.create(glslTOP, 'bright_pass')
bp.par.pixeldat = bd
bp.par.outputresolution = 'custom'; bp.par.resolutionw = 640; bp.par.resolutionh = 360
bp.inputConnectors[0].connect(rend)
bl = pf.create(blurTOP, 'bloom_blur')
bl.par.size.expr = C + 'Bloomsize'
bl.inputConnectors[0].connect(bp)

# HUD text
hud = pf.create(textTOP, 'hud_text')
hud.par.outputresolution = 'custom'; hud.par.resolutionw = 1280; hud.par.resolutionh = 720
hud.par.text.expr = "op('%s/rt').module.HUD" % CP
hud.par.fontsizex = 15
hud.par.alignx = 'left'; hud.par.aligny = 'top'
hud.par.bgcolorr = 0; hud.par.bgcolorg = 0; hud.par.bgcolorb = 0; hud.par.bgalpha = 0
hud.par.fontcolorr = 0.75; hud.par.fontcolorg = 0.95; hud.par.fontcolorb = 1.0
hud.par.positionunit = 'pixels'
log['hudpars'] = [p.name for p in hud.pars() if 'pos' in p.name or 'font' in p.name or 'align' in p.name][:20]

ADDB = '''
uniform vec4 uA;
out vec4 fragColor;
void main(){
    vec3 c = texture(sTD2DInputs[0], vUV.st).rgb + texture(sTD2DInputs[1], vUV.st).rgb * uA.x;
    fragColor = TDOutputSwizzle(vec4(c, 1.0));
}
'''
ad = txt(pf, 'addbloom_glsl', ADDB)
ab = pf.create(glslTOP, 'add_bloom')
ab.par.pixeldat = ad
ab.par.outputresolution = 'custom'; ab.par.resolutionw = 1280; ab.par.resolutionh = 720
ab.inputConnectors[0].connect(rend); ab.inputConnectors[1].connect(bl)
ab.par.vec0name = 'uA'
ab.par.vec0valuex.expr = C + 'Bloomamount'

FINAL = '''
uniform vec4 uF0;  // exposure, bloom, vignette, grain
uniform vec4 uF1;  // chroma, fadeToBlack, docMix, showHud
uniform vec4 uF2;  // time
out vec4 fragColor;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main(){
    vec2 uv = vUV.st;
    vec2 d = uv - 0.5;
    float ch = uF1.x * (0.4 + dot(d, d) * 4.0);
    vec3 r;
    r.r = texture(sTD2DInputs[0], uv + d * ch).r;
    r.g = texture(sTD2DInputs[0], uv).g;
    r.b = texture(sTD2DInputs[0], uv - d * ch).b;
    vec3 c = r;
    c = 1.0 - exp(-c * uF0.x);                               // tone map
    c = pow(c, vec3(0.95));
    float vg = 1.0 - uF0.z * smoothstep(0.25, 0.95, length(d) * 1.35);
    c *= vg;
    c += (hash(uv * vec2(1280.0, 720.0) + uF2.x) - 0.5) * uF0.w;
    vec3 src = texture(sTD2DInputs[1], uv).rgb;
    c = mix(c, src, uF1.z);                                  // documentary: raw footage, no effects
    vec4 h = texture(sTD2DInputs[2], uv);
    c = c + h.rgb * h.a * uF1.w * (1.0 - uF1.z);
    c *= (1.0 - uF1.y);
    fragColor = TDOutputSwizzle(vec4(max(c, 0.0), 1.0));
}
'''
fd = txt(pf, 'final_glsl', FINAL)
fg = pf.create(glslTOP, 'final_pass')
fg.par.pixeldat = fd
fg.par.outputresolution = 'custom'; fg.par.resolutionw = 1280; fg.par.resolutionh = 720
fg.inputConnectors[0].connect(ab)
fg.inputConnectors[1].connect(srcv)
fg.inputConnectors[2].connect(hud)
fg.par.vec0name = 'uF0'
for a, nm in zip('xyzw', ('Exposure', 'Bloomamount', 'Vignette', 'Grain')):
    getattr(fg.par, 'vec0value' + a).expr = C + nm
fg.par.vec1name = 'uF1'
for a, nm in zip('xyzw', ('Chroma', 'Fadeblack', 'Docmix', 'Showhud')):
    getattr(fg.par, 'vec1value' + a).expr = C + nm
fg.par.vec2name = 'uF2'
fg.par.vec2valuex.expr = 'absTime.seconds % 100.0'
out = pf.create(nullTOP, 'OUT_POST'); out.inputConnectors[0].connect(fg)

fin = P.op('RENDER').op('FINAL_OUT')
if fin: fin.destroy()
fin = P.op('RENDER').create(selectTOP, 'FINAL_OUT')
fin.par.top = out.path
log['inputs'] = [fg.inputConnectors[i].connections[0].owner.name if fg.inputConnectors[i].connections else None for i in range(len(fg.inputConnectors))]
log['err'] = [fg.errors(), bp.errors(), hud.errors()]
result = {k: str(v) for k, v in log.items()}
