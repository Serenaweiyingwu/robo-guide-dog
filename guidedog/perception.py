"""What the dog sees: one camera photo -> a structured scene for a blind owner, in Chinese."""

from dataclasses import dataclass, field

SCENE_PROMPT = """你是一只导盲犬的眼睛。照片是导盲犬朝前看到的画面，主人是盲人，就站在导盲犬身后。
只返回一个JSON对象，不要别的文字：
{
  "description": "给盲人主人的一到两句中文播报。先说最重要的安全信息，再说环境。用"前方""左边""右边"和大概步数或米数，不说颜色等视觉细节，不说"照片""画面"。",
  "hazards": [{"what": "台阶/路缘/车辆/站台边缘/坑洼/障碍物等", "where": "前方/左前/右前/左边/右边", "distance_m": 数字, "urgency": "high/medium/low"}],
  "blind_path": {
    "visible": 是否看到盲道（黄色或灰色凸起地砖）,
    "kind": "行进盲道（条纹）/提示盲道（圆点，表示停下、转弯或边缘）/无",
    "blocked": 盲道上是否有东西挡住路线,
    "blockers": ["挡住盲道的东西，如共享单车、汽车、垃圾桶、围栏"],
    "movable_by_people": 挡路的东西路人能不能动手挪开（自行车、电动车、垃圾桶可以；汽车、施工围栏、建筑不行）
  },
  "people_nearby": 附近是否有可以请求帮忙的路人
}
注意：看不清就说看不清，不要编造。没有危险时 hazards 为空数组。
安全第一：绝对不要建议主人走进机动车道、非机动车道或马路；绕行建议只能指向人行道上确实安全的一侧。
如果没有安全的绕行路线，就说"请先停下"，不要给方向。"""


@dataclass
class Scene:
    description: str
    hazards: list = field(default_factory=list)
    blind_path_visible: bool = False
    blind_path_kind: str = "无"
    blocked: bool = False
    blockers: list = field(default_factory=list)
    movable: bool = False
    people_nearby: bool = False

    @classmethod
    def from_json(cls, d: dict) -> "Scene":
        bp = d.get("blind_path") or {}
        return cls(
            description=(d.get("description") or "").strip(),
            hazards=d.get("hazards") or [],
            blind_path_visible=bool(bp.get("visible")),
            blind_path_kind=bp.get("kind") or "无",
            blocked=bool(bp.get("blocked")),
            blockers=bp.get("blockers") or [],
            movable=bool(bp.get("movable_by_people")),
            people_nearby=bool(d.get("people_nearby")),
        )

    @property
    def urgent(self) -> bool:
        return any(h.get("urgency") == "high" for h in self.hazards)


def look(ai, jpeg: bytes, question: str = "") -> Scene:
    """question: what the owner asked, e.g. "前面有什么？" (empty = routine look while walking)."""
    return Scene.from_json(ai.see_json(SCENE_PROMPT, jpeg, question or "主人在走路，看看前方。"))
