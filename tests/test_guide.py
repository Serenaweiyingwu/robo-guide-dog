"""Guide dog decisions, offline (scenes are hand-written, no Doubao calls)."""

from guidedog.guide import Guide
from guidedog.perception import Scene


def scene(**kw):
    return Scene(description=kw.pop("description", "前方是人行道。"), **kw)


BIKES = dict(description="前方盲道被共享单车挡住了。", blind_path_visible=True, blocked=True,
             blockers=["共享单车"], movable=True, people_nearby=True)


def test_quiet_while_walking_unless_something_matters():
    assert Guide().on_scene(scene()) == []


def test_answers_when_asked():
    said = Guide().on_scene(scene(), asked=True)
    assert [(s.to, s.text) for s in said] == [("owner", "前方是人行道。")]


def test_urgent_hazard_is_announced_with_alert():
    said = Guide().on_scene(scene(description="前方一米有台阶。", hazards=[{"what": "台阶", "urgency": "high"}]))
    assert said[0].to == "owner" and said[0].gesture == "alert"


def test_bikes_on_blind_path_tells_owner_then_asks_strangers_once():
    g = Guide()
    said = g.on_scene(scene(**BIKES))
    assert [s.to for s in said] == ["owner", "owner", "stranger"]
    assert "共享单车" in said[-1].text and "导盲犬萝卜" in said[-1].text
    again = g.on_scene(scene(**BIKES))
    assert [s.to for s in again] == ["owner"]  # doesn't repeat the request every look


def test_thanks_strangers_when_cleared():
    g = Guide()
    g.on_scene(scene(**BIKES))
    said = g.on_scene(scene(blind_path_visible=True))
    assert [(s.to, s.text) for s in said] == [("stranger", "谢谢您！"), ("owner", "盲道通了，可以继续走。")]


def test_unmovable_blocker_means_detour_not_asking_strangers():
    said = Guide().on_scene(scene(description="盲道被汽车挡住，请向左绕行。", blocked=True,
                                  blockers=["汽车"], movable=False, people_nearby=True))
    assert [s.to for s in said] == ["owner"]


def test_obstacle_alert_is_spoken_then_dog_looks_to_say_what_it_is():
    from guidedog.obstacles import ObstacleWatch

    alert = ObstacleWatch().update(front_m=0.8)[0]
    say, look = Guide().on_obstacle(alert)
    assert [(s.to, s.text, s.gesture) for s in say] == [("owner", "停，前方一米内有障碍。", "alert")]
    assert look


def test_clear_alert_needs_no_photo():
    from guidedog.obstacles import Alert

    say, look = Guide().on_obstacle(Alert("clear", 3.0, "前方没有障碍了。", False))
    assert say[0].text == "前方没有障碍了。" and not look
