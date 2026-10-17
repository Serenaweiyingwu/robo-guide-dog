# Robo guide dog — notes for Claude sessions

Started 2026-10-18 as the hackathon project (灵机一动 · Soul Hackathon; submission due 2026-10-22 12:00,
on-robot day 10-23). Sister project `~/robo-translator` (translator + Hightorque body) is kept, not abandoned;
its `CLAUDE.md` has the event, Doubao account, Vbot interface and ROS 2 setup notes. Read that too.

## Goal (user, 2026-10-18)
A Chinese-speaking guide dog on the **Vbot 大头**: describe everything in words to the blind owner, and talk
to strangers to move bikes off the blind path (盲道). Persona: 导盲犬萝卜 (wake word "Robo"/萝卜).

## Status
- Vision works with `doubao-seed-2-1-lite-260915` via `Doubao.see_json` (data-URI JPEG), ~2–4 s per photo.
- 12 Wikimedia test photos in `testdata/wikimedia/` (gitignored; licences in `SOURCES.json`): 11/12 judged
  right. Miss: Australian dark-grey tactile strip (`blocked_bin`); yellow Chinese 盲道 always caught.
- **Safety fix**: v1 told the owner to detour left into the traffic lane. Prompt now forbids routing into roads
  and says "请先停下" when there's no safe detour (3/3 after fix). Re-check this whenever the prompt changes.
- `Guide` decisions are unit-tested offline (`tests/test_guide.py`).
- Not built yet: owner voice questions (reuse wake word + ASR from robo-translator), the Vbot body
  (camera `camera_msgs/srv/GetJpegImages`, speaker `AgentToSpeechAudioRaw` 16 kHz, turn to strangers via
  `BaseAction` / voice direction from `WakeupInfo` DOA, head gestures, following). Waiting on Vbot support
  for topic/service names and the Zenoh network setup.

## Working with this user
Never push without an explicit "push"; never enter keys; they're OK spending Doubao tokens on tests but
like to know roughly how many. `.env` holds keys (gitignored); scan history for them before any push.
