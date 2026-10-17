# Kiki guide dog — notes for Claude sessions

**Kiki (导盲犬Kiki)** is a Chinese-speaking guide-dog agent for blind and visually impaired people, built for
**灵机一动 · Soul Hackathon 2026** (organiser She Nicest) to run on the **维他动力 Vbot 大头** robot dog.
It describes the surroundings in words, warns about obstacles, and asks passers-by to move bikes off the
blind path (盲道). Last updated 2026-10-18. Read this first, then `README.md`.

Sister project: `~/robo-translator` (github.com/Serenaweiyingwu/robo-translator) — a translator robot with a
Hightorque body. Kept on purpose for future humanoid work; don't delete or fold it in. Its `CLAUDE.md` has the
longer history (event handbook, Hightorque docs, Doubao console steps).

## Deadlines

| When | What |
|---|---|
| **2026-10-22 12:00** | Readiness submission: environment proof, agent name + description, progress, run proof (screenshot / recording), robot deployment plan. Results 22:00. |
| **2026-10-23** | On-robot day, 上海张江科学会堂: 09:30–12:00 deploy, 13:30–16:30 playground, 16:30 optional 3–5 min stage demo ("Show Me Something Weird"). Robot is exclusively ours (独占分配). No changes to the robot's low-level system or safety settings without staff OK. |

## Where things stand

**Done and tested (31 offline tests, `.venv/bin/pytest`):**
- **Seeing** (`perception.py`): JPEG → Doubao vision → `Scene` (Chinese description, hazards with urgency,
  blind path visible/kind/blocked/blockers/movable, people nearby). ~2–4 s per photo.
  12 Wikimedia photos: 11/12 right; the miss is an Australian dark-grey tactile strip.
- **Safety rule in the prompt**: never route the owner into a road; say "请先停下" if there's no safe detour.
  (v1 sent the owner into the traffic lane.) Re-check with the bikes photos whenever the prompt changes.
- **Judgement** (`guide.py`): quiet unless something matters (or 多说点 mode); urgent hazards get "alert";
  movable blocker + people nearby → tell owner, turn to strangers, ask politely **once**, thank them when clear;
  car/fence → no request, just stop/detour.
- **Obstacles** (`obstacles.py`): fast layer from the dog's own sensors, not vision. Near < 2 m, stop < 1 m
  (0.2 m hysteresis); `terrain_ahead()` finds steps (±8 cm) and drops (> 15 cm, urgent) in the height map.
  Alerts only on change. Fixed phrases so speech is pre-synthesised and instant.
- **Voice** (`voice.py`): wake word Kiki/琪琪/奇奇/七七/…; commands matched locally (停 first, then 跟着我,
  安静, 多说点, 再说一遍, 请人帮忙); anything else is a question for the camera.
- **Dog loop** (`dog.py` `GuideDog`): hear / sense / walk_tick / look / speak; `warm_up()`; acknowledgements
  have `info=False` so 再说一遍 repeats real information. `PhotoCamera` + `LaptopBody` stand in for the robot.
- Live text-mode rehearsal (2026-10-18) worked end to end; two bugs it found are fixed and tested.

**Not done:**
1. **Vbot body + camera** (`VbotBody`, `VbotCamera`): blocked on Vbot support (see below).
2. One **real microphone** run (only text mode tried so far).
3. **Submission** materials for 10-22.

## Waiting on

- **Vbot support** (WeChat **towardsdawn**, note "shenicest参赛"); the user was given a Chinese draft asking for:
  topic/service names for following, speaker audio, BaseAction, HeadCmd, mic audio; **Zenoh** router
  address/port + `ROS_DOMAIN_ID`; SSH (`vbot@<ip>`, may need a public key); how to silence the built-in voice
  agent while we stream audio; docs/examples.
- **Organisers**: robot assignment (asked for Vbot first, then Hightorque Mini Pi Plus 基础款, then RoboParty RP1),
  IP/login. Earlier questions in `~/robo-translator/CLAUDE.md`.

## Next steps (in order)

1. When the network details arrive: join the dog's network from the Mac and run `ros2 topic list -t` /
   `ros2 service list -t` to get every name (most names aren't in the msg files).
2. Write `VbotCamera.snap()` (`camera_msgs/srv/GetJpegImages`, front channel) and `VbotBody`:
   `say()` → `function_msgs/msg/AgentToSpeechAudioRaw` (16 kHz mono int16; request 16000 from Doubao TTS or
   resample from 24 kHz), `stop()` → `ControlFollowing` mode STOP, `follow()` → FOLLOWING/ACCOMPANY,
   `face("stranger")` → `BaseAction` ROTATE_IN_PLACE using DOA from `speech_msgs/WakeupInfo` when available,
   gestures → `BaseAction` MOVE_HEAD / `lowlevel_msg/HeadCmd` (nod, tilt, look around), ear lights/face if exposed.
   Feed `GuideDog.sense()` from `SportModeState.range_obstacle` (**confirm which index is front**) and
   `lowlevel_msg/HeightMap` (units assumed metres), or `function_msgs/srv/GetGuard`.
   Mic: `speech_msgs/msg/SpeechDogToPhone` → existing Doubao ASR.
3. Rehearse with a real voice and record a short demo for the submission.
4. Draft the 10-22 submission (name: "Kiki · 会说话的导盲犬"; deployment plan = step 2).

## Environment

**Keys**: `.env` (gitignored via `.env*`, `!.env.example`), copied from `~/robo-translator/.env`. Never print or
commit them; before every push run a check that neither key string appears in `git log -p origin/main..HEAD`.
If the user must (re)enter a key, give them:
`read -rs "K?Paste key: " && sed -i '' "s|^VAR=.*|VAR=$K|" ~/robo-guide-dog/.env && unset K`
(nano went wrong twice in the translator repo; once it created a stray `".env "` file).

**Doubao / Volcengine** (user's account, default project; free quotas: TTS 20k chars, each ASR 20 h, LLM 500k tokens):
- LLM + vision: Ark `doubao-seed-2-1-lite-260915` (`DOUBAO_MODEL`), images as data-URI JPEG in the content list.
  `GET https://ark.cn-beijing.volces.com/api/v3/models` lists model IDs.
- ASR: `.../api/v3/auc/bigmodel/recognize/flash` with resource **`volc.seedasr.auc`** (the legacy
  `volc.bigasr.auc_turbo` is not granted to new accounts). `lang=None` auto-detects zh/en.
- TTS: `seed-tts-2.0`, voice `zh_female_vv_uranus_bigtts`, 24 kHz PCM by default.
- Usage so far ≈ 45k LLM tokens, ~1k TTS chars. The user is fine spending tokens on tests but likes an estimate first.

**Vbot interfaces** (public msgs: github.com/VitaDynamics/vbot_ros2_msgs, ROS 2 Humble):
built on the Mac in `~/vbot_ws` (15 packages) using the pixi env from `~/rp1-ros`:
`cd ~/vbot_ws && ~/.pixi/bin/pixi run --manifest-path ~/rp1-ros/pixi.toml bash -c "source install/setup.bash && ros2 ..."`.
Rebuilding needs `--cmake-args -DPython_EXECUTABLE=<env python> -DPython3_EXECUTABLE=<same> -DPython_FIND_STRATEGY=LOCATION`
(CMake 4 can't find pixi's Python otherwise). Known names: `/speech/ChatTtsNotification`, `/lightning/loc_cmd`,
`/lightning/save_map`. Forum (forum.vbot.cn): raw mic + streaming playback recently exposed; SSH as `vbot`;
a user hit "Zenoh communication refused", so the dog likely uses **rmw_zenoh** —
`ros-humble-rmw-zenoh-cpp` 0.1.8 is installed in `~/rp1-ros` (`rmw_zenohd` router; run with
`RMW_IMPLEMENTATION=rmw_zenoh_cpp`). The built-in agent accepts custom MCP services (fallback path).
Hardware: 4-mic array (DOA), expression screen, ear lights, 14 joints (12 legs + likely 2 head), UWB
(following likely tracks a UWB tag), depth stereo camera, 16-line LiDAR, 128 TOPS.

**Mac ROS 2**: RoboStack Humble via pixi in `~/rp1-ros` (`~/.pixi/bin/pixi`, installed from the GitHub release
because Homebrew stalled). Network here can drop connections to prefix.dev / Wikimedia; just retry.
macOS has no `timeout` command. Disk is tight (~14 GB free).

## Files

- `guidedog/perception.py`: scene prompt + `Scene` · `guide.py`: decisions (`Say`) · `obstacles.py`: sensor alerts
- `guidedog/voice.py`: wake word + commands · `dog.py`: `GuideDog`, `PhotoCamera`, `LaptopBody`
- `guidedog/doubao.py`, `audio.py`, `config.py`: copied from robo-translator (+ `see_json` for images)
- `testdata/` (gitignored): `wikimedia/` 12 photos + `SOURCES.json` licences, `results_v1.json`, `speech/` WAVs

Try it: `.venv/bin/python -m guidedog talk testdata/wikimedia/blocked_bikes_1.jpg --text --mute`
(type `Kiki，前面有什么？`, or `!front 0.8`, `!step -0.12`, `!clear`, `!tick`).

## Working with this user

- Never `git push` without an explicit "push" in that message. Committing locally is fine.
- Never type passwords or keys; the user signs in and pastes keys themselves.
- They're often mid-workshop: short updates, copy-paste commands, Chinese drafts for messages to organisers.
- Safety matters for this project: describe Kiki as an assistant alongside a white cane, never a replacement.
