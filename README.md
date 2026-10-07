# 4D COLLISION - TWO BODIES THROUGH TIME

TouchDesigner artwork built live from `07.10.2026_03.14.43_REC.mp4` (two grizzly bears fighting on a road, 25.27 s, 634 frames, panning camera).
The whole encounter is turned into one space-time sculpture: `Z = TIME x TIME_DEPTH`. Open `BEAR_COLLISION.toe`; everything lives in `/BEAR_COLLISION`
(the 19 components from the brief + `BEAR_TRACKING/BEAR_A|BEAR_B`).

## Pipeline
1. **Offline CV** (`scripts/cv_stage_a.py`, ~50 min on CPU): Mask R-CNN instance masks, Depth Anything V2 (small), Farneback flow, RANSAC global camera motion
   (the camera pans to follow the bears, so every point is stored in *stabilised* world coordinates).
2. **Pack** (`scripts/pack_bears.py`): two-bear identity tracking (Hungarian matching on position + colour, optical-flow-warped mask prior and k-means split when the
   bears merge into one mask), 768 points per bear per sample (640 interior + 128 contour), interaction signal, contact pairs, shockwave events, audio features,
   float textures + mask/depth/flow videos. 317 samples (12.5 Hz) x 1536 points = 487k points.
3. **TouchDesigner**: Script TOPs load the float textures; one GLSL vertex shader library (`shaders/common.glsl`) places any stored point in 3D (time axis, time bending,
   collision distortion, noise, curl, explosion). Points / contact fibres / temporal mesh / slice frames / shockwaves / scan plane / video plane / dust are GLSL MATs
   instanced per time slice. A 32x1 float texture (`uni_tex`) carries every control to the shaders; `CONTROL_PANEL/rt` drives it every frame.
4. **Clock**: one timeline clock drives all movies (Movie File In locked to timeline; sample *s* is at *s*/12.5 s = source frame 2*s*). Specify-Index mode did not
   seek reliably here, so `root.time.seconds` is set by the runtime and the timeline is paused.

## Modes (TEMPORAL_MODE)
FULL VOLUME, POINT CLOUD, TEMPORAL MESH, TIME SLICES, SLIT SCAN, CONTACT FIELD, HYBRID. TIME_GEOMETRY: LINEAR, CURVE, HELIX, SPIRAL, VORTEX, RING, WAVE.
Colour modes: ORIGINAL RGB, MONOCHROME, TWO COLORS (A/B user colours), TIME GRADIENT, VELOCITY, INTERACTION.

## Controls (`/BEAR_COLLISION/CONTROL_PANEL`)
Pages SOURCE, SEGMENTATION, TRACKING, TIME, DEPTH, GEOMETRY, BEAR A, BEAR B, CONTACT, POINTS, DEFORMATION, PARTICLES, CAMERA, AUDIO, PERFORMANCE (+ POST, RT).
`TIME_DEPTH` is the master (0 = history collapses into the image). `FREEZE_TIME` stops the footage and lets you orbit the finished sculpture; `SCAN_POS` / `SCAN_SPEED`
move the NOW plane through it. `TIME_DIRECTION` FORWARD / REVERSE / PING PONG. `AUTO_SHOW` runs the 14-scene sequence (162 s); set `SHOW_CLOCK` to jump.
`DOCUMENTARY_MIX` = 1 shows the untouched footage.

## Outputs
`SOURCE/SOURCE_VIDEO`, `BACKGROUND_REMOVAL/OUT_BEAR_RGB`, `OUT_BACKGROUND`, `BEAR_SEGMENTATION/OUT_BEAR_MASK|OUT_BEAR_A_MASK|OUT_BEAR_B_MASK`,
`BEAR_TRACKING/OUT_TRACKING` (bearA_x ... interaction_intensity), `DEPTH/OUT_DEPTH`, `OPTICAL_FLOW/OUT_FLOW`, `RENDER/OUT_RENDER`, `RENDER/FINAL_OUT`.

## Rebuilding
`scripts/build_00 ... build_70` recreate the network through the exec bridge (`td_bridge.py`, port 9981, load via Textport `exec(open(r'...\td_bridge.py').read())`;
`tdrun.py file.py` runs a script in TD). `scripts/push_rt.py` re-pushes the runtime module; `scripts/snap.py` / `show_grid.py` render stills.

## What is real and what is approximate (read this)
**Measured / verified in this build** (laptop with Intel UHD 620, TD 2025.33230 non-commercial):
* The 14-scene AUTO_SHOW ran live end to end (162 s, looping) with zero runtime errors at ~22-45 fps (mostly 35-40) at 1280x720, PREVIEW quality (<=56 time slices).
  AUTO_QUALITY lowers the slice count if fps drops under TARGET_FPS (24).
* Present-frame points land on the bears in the footage (checked at the hug at sample 45); mask / bear-RGB / background / depth / flow / source stay frame-synchronous
  (checked at samples 180 and 260 after fixing the timeline loop range).
* All 7 TEMPORAL_MODEs and all 7 TIME_GEOMETRYs render distinct results; FORWARD / REVERSE / PING PONG and FREEZE_TIME behave; the video-audio features change with the footage.
* The tracking debug overlays were reviewed at ~25 of the 317 samples: identity A (left, darker) / B held through the hugs I looked at.

**Approximate or not achieved - be aware:**
* **Segmentation is offline Mask R-CNN, not live.** Mask edges are blobby (28x28 mask grid), thin limbs/ears are lost, and the bear lying on the road around samples ~255-265 and the
  last camera swing (~t300+) are only partly segmented (the mask misses the lying body). When both bears merge into one mask (145 of 317 samples) A/B is split by
  flow-warped previous masks + colour/position k-means + a majority filter; heavy overlaps (e.g. ~t182, ~t286) are only roughly right and identity could swap in moments I did not inspect.
* **Depth is monocular relative depth** (Depth Anything V2 small), normalised per frame - plausible relief, not metric.
* **The camera pans; stabilisation is a RANSAC similarity transform** on the background, so long-range drift accumulates; the present slice is re-aligned to the footage every frame.
* **Point counts:** 317 samples x 1536 points = 487k stored points (the brief's 100k-500k). The renderer draws a thinned set (<=56 slices at PREVIEW; HIGH 110; CINEMATIC 220);
  full density (SAMPLE_STEP 1, ~487k sprites) was not run in real time on this GPU.
* **Gaussian look = soft elliptical point sprites,** not true 3D Gaussian Splatting.
* **Optical flow is Farneback** (not RAFT); velocities stretch sprites and drive VELOCITY colour.
* **1080p:** the OUTPUT_RES switch exists but this non-commercial license keeps the output at 1280x720, so 1080p was not verified.
* **AUDIO:** the footage's own soundtrack is analysed offline (bass/mid/high/transient/amplitude per sample) and drives the optional audio mapping when AUDIO_ENABLE is on; no sound is played in TD.
  LIVE input analysis (AUDIO page) is wired but was NOT tested with a microphone. AUTO_SHOW leaves audio off.
* Camera framing for non-LINEAR time geometries is not auto-fitted (RING clips at some angles) - use CAMERA_DISTANCE / CAMERA_CENTER_BLEND.
* The time slices / slit-scan / temporal-mesh modes were checked at a handful of settings only.

## Gotchas learned (for anyone rebuilding)
* Movie File In `Specify Index` did not seek reliably here -> `Locked` playback with the runtime setting `root.time.seconds` each frame.
* The timeline's loop range defaults to 600 frames; it must be extended (`rangeEnd`) or any time past 10 s wraps. The runtime enforces it.
* Execute DAT frame callbacks only fire while the timeline is playing.
* GLSL TOP exposes only 3 inputs. The Render/post resolution pars carry `+0*absTime.frame` to keep them time-dependent (added defensively; I did not prove it is required - live playback updated correctly with it in place).
* Movie TOPs only deliver new frames while TD's main loop runs (not inside a blocking script) - test them across separate calls.
* Heredocs with apostrophes break in the Bash tool here; write files with the editor tools instead.

## Using this repository
This repo contains the code, shaders and the saved TouchDesigner project (`BEAR_COLLISION.toe`). It does **not** include the source video or anything derived from it
(masks, depth, flow, point clouds, rendered frames, the exported MP4) because the footage is not mine to redistribute. To rebuild with your own two-subject clip:
1. Set `VIDEO` in `scripts/cv_stage_a.py` and `scripts/pack_bears.py`, encode the CFR/all-intra source (`ffmpeg ... -vf crop=...,fps=25 -g 1 data/source_cfr.mp4`, see the README pipeline section).
2. `python scripts/cv_stage_a.py` then `python scripts/pack_bears.py` (needs torch, torchvision, transformers, opencv, scipy; hours on CPU).
3. In TouchDesigner paste the bridge line from "Rebuilding", then run `scripts/build_00 ... build_80` via `python tdrun.py`.
Paths in the scripts are Windows absolute paths (`C:/Users/Utsav/bear-collision`); change `ROOT` for your machine.

## License
Code and shaders: MIT (see `LICENSE`). The bear footage is not covered by this license and is not included.
