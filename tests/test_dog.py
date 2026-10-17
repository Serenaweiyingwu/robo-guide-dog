"""The whole dog with a fake Doubao, fake camera and a recording body (offline)."""

from guidedog.dog import GuideDog

BIKES = {"description": "前方盲道被共享单车挡住了。", "hazards": [],
         "blind_path": {"visible": True, "blocked": True, "blockers": ["共享单车"], "movable_by_people": True},
         "people_nearby": True}
CLEAR = {"description": "前方是人行道，没有障碍。", "hazards": [], "blind_path": {"visible": True}, "people_nearby": False}


class FakeAI:
    def __init__(self, scenes=()):
        self.scenes, self.spoken, self.questions = list(scenes), [], []

    def see_json(self, system, jpeg, text=""):
        self.questions.append(text)
        return self.scenes.pop(0)

    def speak(self, text, lang, rate=24000):
        self.spoken.append(text)
        return b"pcm"


class Camera:
    def snap(self):
        return b"jpeg"


class Body:
    def __init__(self):
        self.events = []

    def say(self, pcm, rate):
        self.events.append("say")

    def face(self, who):
        self.events.append(f"face {who}")

    def gesture(self, name):
        pass

    def stop(self):
        self.events.append("stop")

    def follow(self):
        self.events.append("follow")


def dog(scenes=()):
    ai, body = FakeAI(scenes), Body()
    return GuideDog(ai, Camera(), body, log=lambda *_: None), ai, body


def test_ignores_talk_without_the_name():
    d, ai, body = dog()
    d.hear("今天好冷啊")
    assert ai.spoken == [] and body.events == []


def test_stop_halts_before_speaking():
    d, ai, body = dog()
    d.hear("Kiki，停！")
    assert body.events[0] == "stop" and ai.spoken == ["我停下了。"]


def test_question_takes_a_photo_and_answers_it():
    d, ai, _ = dog([CLEAR])
    d.hear("琪琪，前面有什么？")
    assert ai.questions == ["前面有什么？"] and ai.spoken == ["前方是人行道，没有障碍。"]


def test_repeat_says_the_last_thing_to_the_owner_again():
    d, ai, _ = dog([CLEAR])
    d.hear("Kiki，前面有什么？")
    d.hear("Kiki，再说一遍")
    assert ai.spoken[-1] == "前方是人行道，没有障碍。"


def test_bikes_turns_to_strangers_then_back_to_owner():
    d, ai, body = dog([BIKES])
    d.hear("Kiki，前面有什么？")
    assert "face stranger" in body.events
    assert any("导盲犬Kiki" in t for t in ai.spoken)


def test_owner_can_ask_kiki_to_get_help():
    d, ai, _ = dog([CLEAR])
    d.hear("Kiki，前面有什么？")
    d.hear("Kiki，请人帮忙")
    assert "能麻烦您帮忙挪一下吗" in ai.spoken[-1]


def test_close_obstacle_stops_the_dog_alerts_instantly_then_says_what_it_is():
    d, ai, body = dog([BIKES])
    d.cache["停，前方一米内有障碍。"] = b"cached"
    d.sense(front_m=0.7)
    assert body.events[0] == "stop"
    assert ai.spoken[0] == "前方盲道被共享单车挡住了。"  # the alert itself came from the cache, not TTS
    assert ai.questions == ["前方挡路的是什么？请简短说明。"]


def test_quiet_and_chatty_modes():
    d, ai, _ = dog([CLEAR, CLEAR])
    d.walk_tick()
    assert ai.spoken == []  # nothing important: stays quiet
    d.hear("Kiki，多说点")
    d.walk_tick()
    assert ai.spoken[-1] == "前方是人行道，没有障碍。"


def test_repeat_skips_acknowledgements():
    d, ai, _ = dog([CLEAR])
    d.hear("Kiki，前面有什么？")
    d.hear("Kiki，停")
    d.hear("Kiki，再说一遍")
    assert ai.spoken[-1] == "前方是人行道，没有障碍。"


def test_cleared_path_still_answers_the_question():
    d, ai, _ = dog([BIKES, CLEAR])
    d.hear("Kiki，前面有什么？")
    d.hear("Kiki，前面有什么？")
    assert ai.spoken[-3:] == ["谢谢您！", "盲道通了。", "前方是人行道，没有障碍。"]


def test_obstacle_alert_cuts_off_a_long_description():
    import threading
    import time

    long_text = "前方是一条很长的林荫人行道，" * 3
    d, ai, body = dog([{**CLEAR, "description": long_text}, BIKES])
    spoken_while_busy = []

    def slow_say(pcm, rate):  # a speaker that takes a while, and can be interrupted
        for _ in range(20):
            if d.interrupted.is_set():
                return
            time.sleep(0.02)
        spoken_while_busy.append("finished")

    body.say = slow_say
    talker = threading.Thread(target=d.hear, args=("Kiki，前面有什么？",))
    talker.start()
    time.sleep(0.05)
    d.sense(front_m=0.7)  # obstacle while Kiki is mid-description
    talker.join()
    assert "停，前方一米内有障碍。" in ai.spoken
    assert "stop" in body.events
    assert spoken_while_busy.count("finished") < len(ai.spoken)  # the long description was cut short
