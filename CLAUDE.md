# Robo guide dog — notes for Claude sessions

Started 2026-10-18 as the hackathon project (灵机一动 · Soul Hackathon; submission due 2026-10-22 12:00,
on-robot day 10-23). Sister project `~/robo-translator` (translator + Hightorque body) is kept, not abandoned;
its `CLAUDE.md` has the event, Doubao account, Vbot interface and ROS 2 setup notes. Read that too.

## Goal (user, 2026-10-18)
A Chinese-speaking guide dog on the **Vbot 大头**: describe everything in words to the blind owner, and talk
to strangers to move bikes off the blind path (盲道). Persona: **导盲犬Kiki** (renamed from 萝卜 on 2026-10-18; wake word accepts Kiki/琪琪/奇奇/七七...).

## Status
- Vision works with `doubao-seed-2-1-lite-260915` via `Doubao.see_json` (data-URI JPEG), ~2–4 s per photo.
- 12 Wikimedia test photos in `testdata/wikimedia/` (gitignored; licences in `SOURCES.json`): 11/12 judged
  right. Miss: Australian dark-grey tactile strip (`blocked_bin`); yellow Chinese 盲道 always caught.
- **Safety fix**: v1 told the owner to detour left into the traffic lane. Prompt now forbids routing into roads
  and says "请先停下" when there's no safe detour (3/3 after fix). Re-check this whenever the prompt changes.
- `Guide` decisions are unit-tested offline (`tests/test_guide.py`).
- **Obstacle checks (2026-10-18)**, `guidedog/obstacles.py`: fast layer from the dog's sensors, not vision.
  `ObstacleWatch.update(front_m, terrain)` gives alerts only on change (near < 2 m, stop < 1 m, 0.2 m
  hysteresis; step ±8 cm, drop > 15 cm urgent). `terrain_ahead()` scans the Vbot `lowlevel_msg/HeightMap` in a
  0.4 m corridor 0.3–2 m ahead. Fixed phrases (`PHRASES`) so TTS can be pre-synthesised for instant playback.
  `Guide.on_obstacle` speaks the alert, then asks for a photo to say *what* it is. Sources on the dog:
  `lowlevel_msg/SportModeState.range_obstacle` (float[4] distances; **direction order unknown**, confirm on the
  robot), `function_msgs/srv/GetGuard` (front/left/right/rear occupancy + has_obstacle), HeightMap units
  assumed metres. Tested on simulated readings only.
- **Voice + dog loop (2026-10-18)**: `voice.py` (wake regex Kiki/琪琪/奇奇/七七…, local command patterns, "停"
  first), `dog.py` `GuideDog` (hear / sense / walk_tick / look / speak; `warm_up()` pre-synthesises fixed
  phrases; acks have `info=False` so "再说一遍" repeats real information), `PhotoCamera` + `LaptopBody` stand-ins,
  `python -m guidedog talk ... --text` with `!front/!step/!clear/!tick` sensor simulation. 31 offline tests.
  Live text-mode run 2026-10-18 found + fixed: false "path cleared" skipping the description, and repeat
  echoing acknowledgements. `PhotoCamera` cycles photos, so a follow-up look sees a *different* scene
  (test artifact, not real-world behaviour).
- Not built yet: the Vbot body
  (camera `camera_msgs/srv/GetJpegImages`, speaker `AgentToSpeechAudioRaw` 16 kHz, turn to strangers via
  `BaseAction` / voice direction from `WakeupInfo` DOA, head gestures, following). Waiting on Vbot support
  for topic/service names and the Zenoh network setup.

## Working with this user
Never push without an explicit "push"; never enter keys; they're OK spending Doubao tokens on tests but
like to know roughly how many. `.env` holds keys (gitignored); scan history for them before any push.
