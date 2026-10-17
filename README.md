# 萝卜 Robo — a language guide dog (导盲犬)

A guide-dog agent for blind and visually impaired people, built for 灵机一动 · Soul Hackathon 2026
on the 维他动力 Vbot 大头 robot dog. It speaks Chinese.

- **Describes the world in words** to its owner: steps, kerbs, platform edges, crossings, what's around.
- **Keeps blind paths (盲道) clear**: when shared bikes block the path it tells the owner, then turns to
  people nearby and politely asks them to move the bikes, and thanks them afterwards.
- **Knows what it can't fix**: a car or construction fence is a detour, not a request to strangers, and it
  never suggests stepping into the road.

It is an assistant alongside a white cane, not a replacement: each look takes ~3 s, so the dog's own
obstacle avoidance handles split-second safety and Robo adds the words.

## How it works

```
camera photo ─► Doubao vision model ─► Scene (description, hazards, blind path blocked? by what? movable?
                                             people nearby?) ─► Guide decides what to say, to whom ─► Chinese TTS
```

- `guidedog/perception.py`: the prompt and `Scene`
- `guidedog/guide.py`: decisions (quiet unless something matters, ask strangers once, thank them)
- `guidedog/doubao.py`: Doubao speech recognition, Ark LLM (also vision), TTS

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                                   # Volcengine keys (same as robo-translator)
.venv/bin/python -m guidedog look photo.jpg            # routine look
.venv/bin/python -m guidedog look photo.jpg --ask "前面有什么？" --speak
.venv/bin/pytest                                       # offline tests
```
