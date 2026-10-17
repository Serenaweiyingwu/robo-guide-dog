"""Kiki: ties together hearing, seeing, obstacle sensing, judgement and speech.

The body and camera are small interfaces so the same dog runs on a laptop (photos + speakers) or the Vbot.
"""

import itertools
import threading

from .doubao import TTS_SAMPLE_RATE
from .guide import Guide, Say
from .obstacles import PHRASES, ObstacleWatch
from .perception import look
from .voice import parse


class PhotoCamera:
    """Stands in for the dog's camera: returns the given photos in turn."""

    def __init__(self, paths):
        self.photos = itertools.cycle(paths)

    def snap(self) -> bytes:
        return open(next(self.photos), "rb").read()


class LaptopBody:
    """Stands in for the dog's body: prints movements, plays speech on the laptop."""

    def __init__(self, mute=False, log=print):
        self.mute, self.log = mute, log

    def interrupt(self) -> None:
        if not self.mute:
            import sounddevice

            sounddevice.stop()

    def say(self, pcm: bytes, rate: int) -> None:
        if not self.mute and pcm:
            from .audio import play

            play(pcm, rate)

    def face(self, who: str) -> None:
        self.log(f"  [body] turns to the {who}")

    def gesture(self, name: str) -> None:
        if name:
            self.log(f"  [body] {name}")

    def stop(self) -> None:
        self.log("  [body] STOPS")

    def follow(self) -> None:
        self.log("  [body] starts following the owner")


class GuideDog:
    def __init__(self, ai, camera, body, log=print):
        self.ai, self.camera, self.body, self.log = ai, camera, body, log
        self.guide, self.watch = Guide(), ObstacleWatch()
        self.last = None  # last thing said to the owner, for "repeat"
        self.last_scene = None
        self.cache = {}  # pre-synthesised speech for fixed phrases (instant alerts)
        self.facing = "owner"
        self.rate = getattr(body, "rate", TTS_SAMPLE_RATE)  # speech sample rate the body plays
        self.lock = threading.RLock()  # one thing at a time: sensing runs on its own thread
        self.interrupted = threading.Event()  # an alert cuts off whatever Kiki is saying

    def warm_up(self) -> None:
        """Synthesise the fixed alert phrases once, so alerts play with no network delay."""
        for text in [*PHRASES.values(), "好的。", "我停下了。", "好的，我跟着你。", "好的，我少说一点。", "好的，我会随时告诉你。"]:
            self.cache[text] = self.ai.speak(text, "zh", self.rate)

    # ---- inputs ----

    def hear(self, utterance: str) -> None:
        h = parse(utterance)
        if h.kind == "none":
            return
        if h.kind == "stop":
            self.body.stop()  # immediately, even if Kiki is in the middle of saying something
        with self.lock:
            self._hear(h, utterance)

    def _hear(self, h, utterance: str) -> None:
        self.log(f"owner: {utterance}")
        if h.kind == "stop":
            self.speak([Say("owner", "我停下了。", "", info=False)])
        elif h.kind == "follow":
            self.body.follow()
            self.speak([Say("owner", "好的，我跟着你。", "nod", info=False)])
        elif h.kind == "quiet":
            self.guide.chatty = False
            self.speak([Say("owner", "好的，我少说一点。", "nod", info=False)])
        elif h.kind == "chatty":
            self.guide.chatty = True
            self.speak([Say("owner", "好的，我会随时告诉你。", "nod", info=False)])
        elif h.kind == "repeat":
            self.speak([self.last or Say("owner", "我还没告诉你什么。", "", info=False)])
        elif h.kind == "ask_help":
            scene = self.last_scene or look(self.ai, self.camera.snap())
            self.speak(self.guide.ask_for_help(scene))
        else:  # a question about the surroundings
            self.look(h.text)

    def sense(self, front_m=None, terrain=None) -> None:
        """Feed sensor readings (many times a second); speaks only when something changes."""
        alerts = self.watch.update(front_m, terrain)
        if any(a.urgent for a in alerts):
            self.body.stop()  # immediately, before waiting for any speech in progress
        if any(a.kind != "clear" for a in alerts):  # cut off a description so the warning isn't delayed
            self.interrupted.set()
            getattr(self.body, "interrupt", lambda: None)()
        for alert in alerts:
            say, want_photo = self.guide.on_obstacle(alert)
            with self.lock:
                self.interrupted.clear()
                self.speak(say)
                if want_photo:
                    self.look("前方挡路的是什么？请简短说明。")

    def walk_tick(self) -> None:
        """Routine look while walking (e.g. every few seconds)."""
        with self.lock:
            self.look("")

    def look(self, question: str) -> None:
        scene = look(self.ai, self.camera.snap(), question)
        self.last_scene = scene
        self.speak(self.guide.on_scene(scene, asked=bool(question)))

    # ---- output ----

    def speak(self, says: list) -> None:
        for s in says:
            if self.interrupted.is_set():  # an alert is waiting: drop the rest of this
                return
            if s.to != self.facing:
                self.body.face(s.to)
                self.facing = s.to
            self.body.gesture(s.gesture)
            self.log(f"Kiki → {s.to}: {s.text}")
            pcm = self.cache.get(s.text) or self.ai.speak(s.text, "zh", self.rate)
            self.body.say(pcm, self.rate)
            if s.to == "owner" and s.info:
                self.last = s
