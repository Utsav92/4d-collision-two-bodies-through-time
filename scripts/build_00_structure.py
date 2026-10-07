"""MVP1: project skeleton, CONTROL_PANEL, SOURCE video. Run through tdrun.py. Idempotent."""
ROOT = 'C:/Users/Utsav/bear-collision'
log = {}
old = op('/BEAR_COLLISION')
if old:
    old.destroy()
P = root.create(baseCOMP, 'BEAR_COLLISION')
P.nodeX = 0; P.nodeY = -600

NAMES = ['SOURCE', 'BACKGROUND_REMOVAL', 'BEAR_SEGMENTATION', 'BEAR_TRACKING', 'OPTICAL_FLOW', 'DEPTH', 'TEMPORAL_BUFFER',
         'SPACETIME_VOLUME', 'CONTACT_FIELD', 'POINT_CLOUD', 'TEMPORAL_MESH', 'GLSL_DEFORMATION', 'PARTICLES', 'CAMERA',
         'AUDIO', 'PERFORMANCE', 'RENDER', 'POST_FX', 'CONTROL_PANEL']
for i, n in enumerate(NAMES):
    c = P.create(baseCOMP, n)
    c.nodeX = (i % 5) * 220; c.nodeY = -(i // 5) * 160
tr = P.op('BEAR_TRACKING')
tr.create(baseCOMP, 'BEAR_A'); tr.create(baseCOMP, 'BEAR_B')

# ---------------------------------------------------------------- CONTROL_PANEL
ctrl = P.op('CONTROL_PANEL')


def page(name):
    return ctrl.appendCustomPage(name)


def addf(pg, name, label, default, lo, hi, kind='float'):
    if kind == 'float': p = pg.appendFloat(name, label=label)[0]
    elif kind == 'int': p = pg.appendInt(name, label=label)[0]
    elif kind == 'toggle': p = pg.appendToggle(name, label=label)[0]
    elif kind == 'rgb': p = pg.appendRGB(name, label=label)
    if kind == 'rgb':
        for q, v in zip(p, default):
            q.default = v; q.val = v
        return p
    p.default = default; p.val = default
    if kind != 'toggle':
        p.min = lo; p.max = hi; p.clampMin = False; p.clampMax = False
        p.normMin = lo; p.normMax = hi
    return p


def addm(pg, name, label, names, labels, default):
    p = pg.appendMenu(name, label=label)[0]
    p.menuNames = names; p.menuLabels = labels
    p.default = default; p.val = default
    return p


NS = 316   # last sample index (317 samples)
pg = page('SOURCE')
addf(pg, 'Playhead', 'PLAYHEAD (sample)', 0.0, 0, NS)
addf(pg, 'Playing', 'PLAYING', 1, 0, 1, 'toggle')
addf(pg, 'Playspeed', 'PLAY_SPEED', 1.0, 0, 4)
addm(pg, 'Timedirection', 'TIME_DIRECTION', ['forward', 'reverse', 'pingpong'], ['FORWARD', 'REVERSE', 'PING PONG'], 'forward')
addf(pg, 'Freezetime', 'FREEZE_TIME', 0, 0, 1, 'toggle')
addf(pg, 'Sourcemix', 'SOURCE_VIDEO_MIX', 0.0, 0, 1)
addf(pg, 'Videoframe', 'VIDEO_FRAME (rt)', 0.0, 0, 632)

pg = page('SEGMENTATION')
addf(pg, 'Maskthreshold', 'MASK_THRESHOLD', 0.5, 0, 1)
addf(pg, 'Maskfeather', 'MASK_FEATHER', 1.5, 0, 20)
addf(pg, 'Erode', 'ERODE', 0.0, 0, 8)
addf(pg, 'Dilate', 'DILATE', 0.0, 0, 8)
addf(pg, 'Edgecleanup', 'EDGE_CLEANUP', 0.5, 0, 1)
addf(pg, 'Backgroundsuppression', 'BACKGROUND_SUPPRESSION', 1.0, 0, 1)

pg = page('TRACKING')
addf(pg, 'Contactthreshold', 'CONTACT_THRESHOLD', 0.55, 0.02, 3.0)
addf(pg, 'Interactionsmooth', 'INTERACTION_SMOOTH', 0.35, 0, 1)
for n in ['bearA_x', 'bearA_y', 'bearB_x', 'bearB_y', 'bear_distance', 'bearA_velocity', 'bearB_velocity', 'relative_velocity', 'interaction_intensity']:
    addf(pg, n.replace('_', '').lower().capitalize(), n, 0.0, -10, 10)

pg = page('TIME')
addf(pg, 'Timedepth', 'TIME_DEPTH', 0.0, 0, 80)
addf(pg, 'Historylength', 'HISTORY_LENGTH', 317, 8, 317, 'int')
addm(pg, 'Temporalmode', 'TEMPORAL_MODE', ['fullvolume', 'pointcloud', 'temporalmesh', 'timeslices', 'slitscan', 'contactfield', 'hybrid'],
     ['FULL VOLUME', 'POINT CLOUD', 'TEMPORAL MESH', 'TIME SLICES', 'SLIT SCAN', 'CONTACT FIELD', 'HYBRID'], 'pointcloud')
addm(pg, 'Timegeometry', 'TIME_GEOMETRY', ['linear', 'curve', 'helix', 'spiral', 'vortex', 'ring', 'wave'],
     ['LINEAR', 'CURVE', 'HELIX', 'SPIRAL', 'VORTEX', 'RING', 'WAVE'], 'linear')
addf(pg, 'Temporalbend', 'TEMPORAL_BEND', 0.0, 0, 1)
addf(pg, 'Temporaltwist', 'TEMPORAL_TWIST', 1.0, 0, 6)
addf(pg, 'Bendradius', 'BEND_RADIUS', 3.0, 0.2, 14)
addf(pg, 'Slicespacing', 'SLICE_SPACING', 12, 2, 40, 'int')
addf(pg, 'Slicethickness', 'SLICE_THICKNESS', 1.0, 0.2, 4)
addf(pg, 'Sliceopacity', 'SLICE_OPACITY', 0.8, 0, 1.5)
addf(pg, 'Slicecount', 'SLICE_COUNT', 24, 2, 80, 'int')
addf(pg, 'Slitpos', 'SLIT_POS', 0.5, 0, 1)
addf(pg, 'Slitwidth', 'SLIT_WIDTH', 0.08, 0.005, 0.5)
addf(pg, 'Samplestep', 'SAMPLE_STEP', 4, 1, 12, 'int')
addf(pg, 'Revealfull', 'REVEAL_FULL', 0.0, 0, 1)
addf(pg, 'Scanpos', 'SCAN_POS', 1.0, 0, 1)
addf(pg, 'Scanspeed', 'SCAN_SPEED', 0.0, 0, 2)

pg = page('DEPTH')
addf(pg, 'Depthscale', 'DEPTH_SCALE', 1.0, 0, 5)
addf(pg, 'Depthcontrast', 'DEPTH_CONTRAST', 1.0, 0.2, 4)
addf(pg, 'Depthsmoothness', 'DEPTH_SMOOTHNESS', 0.5, 0, 1)
addf(pg, 'Depthinfluence', 'DEPTH_INFLUENCE', 1.0, 0, 1)

pg = page('GEOMETRY')
addf(pg, 'Bearseparation', 'BEAR_SEPARATION', 0.0, 0, 6)
addf(pg, 'Motionstretch', 'MOTION_STRETCH', 1.0, 0, 6)
addf(pg, 'Meshopacity', 'MESH_OPACITY', 0.5, 0, 1.5)
addf(pg, 'Showscanplane', 'SHOW_SCAN_PLANE', 1, 0, 1, 'toggle')
addf(pg, 'Showbboxes', 'SHOW_BBOXES', 0, 0, 1, 'toggle')

pg = page('BEAR A')
addf(pg, 'Showa', 'SHOW_BEAR_A', 1, 0, 1, 'toggle')
addf(pg, 'Colora', 'COLOR_A', (1.0, 0.55, 0.12), 0, 1, 'rgb')
pg = page('BEAR B')
addf(pg, 'Showb', 'SHOW_BEAR_B', 1, 0, 1, 'toggle')
addf(pg, 'Colorb', 'COLOR_B', (0.15, 0.7, 1.0), 0, 1, 'rgb')

pg = page('CONTACT')
addf(pg, 'Showcontact', 'CONTACT_FIELD', 1, 0, 1, 'toggle')
addf(pg, 'Contactpersistence', 'CONTACT_PERSISTENCE', 1.0, 0, 1)
addf(pg, 'Contactdensity', 'CONTACT_DENSITY', 1.0, 0, 1)
addf(pg, 'Contactwobble', 'CONTACT_WOBBLE', 0.5, 0, 2)
addf(pg, 'Showshock', 'SHOW_SHOCKWAVES', 1, 0, 1, 'toggle')
addf(pg, 'Shockspeed', 'SHOCK_SPEED', 1.0, 0.1, 4)
addf(pg, 'Contactbright', 'CONTACT_BRIGHTNESS', 1.0, 0, 3)

pg = page('POINTS')
addf(pg, 'Pointdensity', 'POINT_DENSITY', 1.0, 0, 1)
addf(pg, 'Pointsize', 'POINT_SIZE', 1.0, 0.2, 5)
addf(pg, 'Splatopacity', 'SPLAT_OPACITY', 0.8, 0, 2)
addf(pg, 'Gausslook', 'GAUSSIAN_LOOK', 1.0, 0, 1)
addm(pg, 'Colormode', 'BEAR_COLOR_MODE', ['original', 'mono', 'twocolors', 'timegradient', 'velocity', 'interaction'],
     ['ORIGINAL RGB', 'MONOCHROME', 'TWO COLORS', 'TIME GRADIENT', 'VELOCITY', 'INTERACTION'], 'original')
addf(pg, 'Temporalfade', 'TEMPORAL_FADE', 0.5, 0, 1)
addf(pg, 'Temporaldecay', 'TEMPORAL_DECAY', 0.0, 0, 1)
addf(pg, 'Pastpersistence', 'PAST_PERSISTENCE', 1.0, 0.2, 3)
addf(pg, 'Ageopacity', 'AGE_OPACITY', 1.0, 0, 1)
addf(pg, 'Agepointsize', 'AGE_POINT_SIZE', 0.5, 0, 2)
addf(pg, 'Pointstride', 'POINT_STRIDE', 1, 1, 8, 'int')

pg = page('DEFORMATION')
addf(pg, 'Noiseamount', 'NOISE_AMOUNT', 0.0, 0, 3)
addf(pg, 'Noisescale', 'NOISE_SCALE', 1.0, 0.1, 6)
addf(pg, 'Noisespeed', 'NOISE_SPEED', 0.4, 0, 3)
addf(pg, 'Temporalcurl', 'TEMPORAL_CURL', 0.0, 0, 3)
addf(pg, 'Collisionstrength', 'COLLISION_STRENGTH', 1.0, 0, 4)
addf(pg, 'Turbulence', 'TURBULENCE', 0.0, 0, 3)
addf(pg, 'Explode', 'EXPLODE', 0.0, 0, 1)
addf(pg, 'Explodeforce', 'EXPLODE_FORCE', 6.0, 0, 30)
addf(pg, 'Dissolve', 'DISSOLVE', 0.0, 0, 1)

pg = page('PARTICLES')
addf(pg, 'Showdust', 'SHOW_DUST', 1, 0, 1, 'toggle')
addf(pg, 'Dustamount', 'DUST_AMOUNT', 0.6, 0, 1)
addf(pg, 'Dustsize', 'DUST_SIZE', 1.0, 0.2, 4)

pg = page('CAMERA')
addf(pg, 'Camorbit', 'CAMERA_ORBIT', 0.0, -360, 360)
addf(pg, 'Camelevation', 'CAMERA_ELEVATION', 0.0, -89, 89)
addf(pg, 'Camdistance', 'CAMERA_DISTANCE', 9.0, 1, 200)
addf(pg, 'Camfov', 'CAMERA_FOV', 38.0, 8, 100)
addf(pg, 'Autoorbit', 'AUTO_ORBIT', 0, 0, 1, 'toggle')
addf(pg, 'Orbitspeed', 'ORBIT_SPEED', 8.0, -60, 60)
addf(pg, 'Camcenter', 'CAMERA_CENTER_BLEND', 0.0, 0, 1)

pg = page('AUDIO')
addf(pg, 'Audioenable', 'AUDIO_ENABLE', 0, 0, 1, 'toggle')
addm(pg, 'Audiosource', 'AUDIO_SOURCE', ['video', 'live'], ['VIDEO AUDIO (precomputed)', 'LIVE INPUT'], 'video')
addf(pg, 'Audiogain', 'AUDIO_GAIN', 1.0, 0, 4)
for n in ['Bass', 'Mid', 'High', 'Transient', 'Amplitude']:
    addf(pg, 'Au' + n.lower(), n.upper(), 0.0, 0, 1)

pg = page('PERFORMANCE')
addf(pg, 'Autoshow', 'AUTO_SHOW', 0, 0, 1, 'toggle')
addf(pg, 'Showclock', 'SHOW_CLOCK', 0.0, 0, 400)
addf(pg, 'Showscene', 'SCENE_INDEX', 0, 0, 14, 'int')
addm(pg, 'Qualitymode', 'QUALITY_MODE', ['preview', 'high', 'cinematic'], ['PREVIEW', 'HIGH', 'CINEMATIC'], 'preview')
addf(pg, 'Showhud', 'SHOW_HUD', 1, 0, 1, 'toggle')

# ---------------------------------------------------------------- SOURCE : Movie File In -> 1280x720 normalised
src = P.op('SOURCE')
mv = src.create(moviefileinTOP, 'moviein')
mv.par.file = ROOT + '/data/source_cfr.mp4'
mv.par.play = False
mv.par.playmode = 'specify'
mv.par.index.expr = "op('/BEAR_COLLISION/CONTROL_PANEL').par.Videoframe"
fit = src.create(fitTOP, 'fit720')
fit.par.outputresolution = 'custom'; fit.par.resolutionw = 1280; fit.par.resolutionh = 720
fit.inputConnectors[0].connect(mv)
nul = src.create(nullTOP, 'SOURCE_VIDEO')
nul.inputConnectors[0].connect(fit)
root.time.play = True
root.time.end = 360000
root.time.rangeStart = 1; root.time.rangeEnd = 360000; root.time.loop = False
log['mv'] = (mv.width, mv.height, mv.par.file.eval())
log['fit'] = (fit.width, fit.height)
result = log
