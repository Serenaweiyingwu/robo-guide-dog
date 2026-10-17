"""Obstacle alerts from simulated sensor readings (offline)."""

import math

from guidedog.obstacles import ObstacleWatch, terrain_ahead


def kinds(alerts):
    return [a.kind for a in alerts]


def test_approaching_an_obstacle_warns_then_says_stop_once():
    w = ObstacleWatch()
    seen = [kinds(w.update(front_m=d)) for d in [3.0, 2.5, 1.8, 1.5, 0.9, 0.8, 0.7]]
    assert seen == [[], [], ["near"], [], ["stop"], [], []]


def test_no_flicker_around_a_threshold_and_clear_when_gone():
    w = ObstacleWatch()
    w.update(front_m=1.5)  # near
    assert [kinds(w.update(front_m=d)) for d in [2.05, 1.95, 2.1]] == [[], [], []]  # within hysteresis
    assert kinds(w.update(front_m=2.5)) == ["clear"]


def test_stop_alert_is_urgent():
    a = ObstacleWatch().update(front_m=0.6)
    assert kinds(a) == ["stop"] and a[0].urgent


def flat_map(size=40, res=0.1, h=0.0):
    return [h] * (size * size), size, size, res, (-2.0, -2.0)


def with_step(change, at_x=1.0):
    data, w, hgt, res, origin = flat_map()
    for iy in range(hgt):
        for ix in range(w):
            if ix * res + origin[0] >= at_x:
                data[w * iy + ix] = change
    return data, w, hgt, res, origin


def test_flat_ground_has_no_terrain_alert():
    assert terrain_ahead(*flat_map(), pos=(0, 0), yaw=0.0) is None


def test_step_down_ahead_is_found_at_the_right_distance():
    d, change = terrain_ahead(*with_step(-0.12), pos=(0, 0), yaw=0.0)
    assert abs(d - 1.0) < 0.11 and change < -0.1


def test_step_behind_the_dog_is_ignored():
    assert terrain_ahead(*with_step(-0.12), pos=(0, 0), yaw=math.pi) is None


def test_deep_drop_is_urgent_and_step_up_is_not():
    w = ObstacleWatch()
    drop = w.update(terrain=(1.5, -0.3))
    assert kinds(drop) == ["drop"] and drop[0].urgent
    w2 = ObstacleWatch()
    up = w2.update(terrain=(1.5, 0.12))
    assert kinds(up) == ["step_up"] and not up[0].urgent


def test_terrain_alert_repeats_only_after_it_was_gone():
    w = ObstacleWatch()
    assert kinds(w.update(terrain=(1.5, -0.12))) == ["step_down"]
    assert kinds(w.update(terrain=(1.2, -0.12))) == []
    w.update(terrain=None)
    assert kinds(w.update(terrain=(1.5, -0.12))) == ["step_down"]
