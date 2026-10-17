"""Fast obstacle checks from the dog's own sensors (no vision model, so it can run many times a second).

Inputs are plain numbers so this works with any source:
- front distance [m] to the nearest obstacle (Vbot `SportModeState.range_obstacle` / `GetGuard`)
- the ground ahead, from the Vbot `HeightMap`: see `terrain_ahead`
Outputs are alert events, only when something changes, so the owner isn't nagged.
"""

import math
from dataclasses import dataclass

NEAR_M = 2.0  # "there is something ahead"
STOP_M = 1.0  # "stop now"
STEP_M = 0.08  # height change that counts as a step or kerb
DROP_M = 0.15  # a drop this deep is dangerous


@dataclass
class Alert:
    kind: str  # stop, near, clear, step_up, step_down, drop
    distance_m: float
    text: str  # fixed phrase, so speech can be pre-synthesised and played instantly
    urgent: bool


PHRASES = {
    "stop": "停，前方一米内有障碍。",
    "near": "注意，前方有障碍。",
    "clear": "前方没有障碍了。",
    "step_up": "注意，前方有台阶向上。",
    "step_down": "注意，前方有台阶向下。",
    "drop": "停，前方有落差。",
}


def terrain_ahead(data, width, height, resolution, origin, pos, yaw, start=0.3, end=2.0, half_width=0.2):
    """Scan the height map in a corridor in front of the dog.

    Returns (distance_m, height_change_m) of the first cell whose height differs from the ground under the
    dog by more than STEP_M, or None if the corridor ahead is flat. Unknown cells (NaN) are skipped.
    """

    def cell(x, y):
        ix, iy = int((x - origin[0]) / resolution), int((y - origin[1]) / resolution)
        if 0 <= ix < width and 0 <= iy < height:
            v = data[width * iy + ix]
            return None if v is None or math.isnan(v) else v
        return None

    ground = cell(pos[0], pos[1])
    if ground is None:
        return None
    cos, sin = math.cos(yaw), math.sin(yaw)
    d = start
    while d <= end:
        heights = []
        s = -half_width
        while s <= half_width + 1e-9:  # sample across the corridor so a narrow step isn't missed
            h = cell(pos[0] + d * cos - s * sin, pos[1] + d * sin + s * cos)
            if h is not None:
                heights.append(h)
            s += resolution
        if heights:
            change = max(heights, key=lambda h: abs(h - ground)) - ground
            if abs(change) > STEP_M:
                return d, change
        d += resolution
    return None


class ObstacleWatch:
    """Turns a stream of readings into alerts, with hysteresis so it only speaks on changes."""

    def __init__(self):
        self.level = "clear"  # clear, near, stop
        self.terrain = None  # last terrain alert kind

    def update(self, front_m=None, terrain=None) -> list:
        alerts = []
        if front_m is not None:
            level = "stop" if front_m < STOP_M else "near" if front_m < NEAR_M else "clear"
            # a little hysteresis: only relax a level once clearly past the threshold
            if level != self.level and not self._just_inside(front_m, level):
                if level != "clear" or self.level != "clear":
                    alerts.append(Alert(level, front_m, PHRASES[level], level == "stop"))
                self.level = level
        if terrain is not None:
            dist, change = terrain
            kind = "drop" if change < -DROP_M else "step_down" if change < 0 else "step_up"
            if kind != self.terrain:
                alerts.append(Alert(kind, dist, PHRASES[kind], kind == "drop" or dist < STOP_M))
            self.terrain = kind
        else:
            self.terrain = None
        return alerts

    def _just_inside(self, front_m, new_level):
        """Ignore relaxing (stop->near, near->clear) until 0.2 m past the threshold, to avoid flicker."""
        if self.level == "stop" and new_level != "stop":
            return front_m < STOP_M + 0.2
        if self.level == "near" and new_level == "clear":
            return front_m < NEAR_M + 0.2
        return False
