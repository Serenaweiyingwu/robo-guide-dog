from guidedog.voice import parse


def test_needs_the_wake_word():
    assert parse("前面有什么？").kind == "none"
    assert parse("我觉得今天天气不错").kind == "none"


def test_wake_word_spellings():
    for w in ["Kiki", "kiki", "琪琪", "奇奇", "七七", "嘿Kiki", "Key key"]:
        assert parse(f"{w}，前面有什么？").kind == "look", w


def test_questions_go_to_the_camera():
    h = parse("琪琪，盲道在哪里？")
    assert h.kind == "look" and h.text == "盲道在哪里？"
    assert parse("Kiki").text == "前面有什么？"  # just the name = what's ahead


def test_commands():
    cases = {"停！": "stop", "别动": "stop", "跟着我": "follow", "走吧": "follow", "安静一点": "quiet",
             "多说点": "chatty", "再说一遍": "repeat", "请人帮忙挪一下车": "ask_help"}
    for said, kind in cases.items():
        assert parse(f"Kiki，{said}").kind == kind, said


def test_stop_wins_over_everything_else():
    assert parse("Kiki，停，别跟着我").kind == "stop"
