"""The guide dog's judgement: given what it sees, what to say, to whom, and with which body language."""

from dataclasses import dataclass

from .obstacles import Alert
from .perception import Scene


@dataclass
class Say:
    to: str  # "owner" or "stranger"
    text: str
    gesture: str = ""  # alert, nod, look_around, happy, ...
    info: bool = True  # real information (worth repeating), not an acknowledgement like "好的"


class Guide:
    def __init__(self, name: str = "Kiki"):
        self.name = name
        self.asking_for_help = False  # waiting for strangers to clear the blind path
        self.chatty = False  # describe every routine look, not only when something matters

    def on_obstacle(self, alert: Alert) -> tuple:
        """Sensor alert -> (what to say right now, whether to take a photo to say what it is)."""
        say = [Say("owner", alert.text, "alert" if alert.urgent else "nod")]
        return say, alert.kind in ("stop", "near", "drop")

    def on_scene(self, scene: Scene, asked: bool = False) -> list:
        """asked=True when the owner asked a question; otherwise this is a routine look while walking."""
        out = []
        if self.asking_for_help and not scene.blocked:
            self.asking_for_help = False
            out += [Say("stranger", "谢谢您！", "happy"), Say("owner", "盲道通了。", "nod")]
        if asked or self.chatty or scene.urgent or scene.blocked:
            out.append(Say("owner", scene.description, "alert" if scene.urgent else "nod"))
        if scene.blocked and scene.movable and scene.people_nearby and not self.asking_for_help:
            out += self.ask_for_help(scene)
        return out

    def ask_for_help(self, scene: Scene) -> list:
        """Ask passers-by to clear the way (automatically, or when the owner asks Kiki to)."""
        self.asking_for_help = True
        what = "、".join(scene.blockers) or "东西"
        problem = f"盲道被{what}挡住了" if scene.blocked else f"前面有{what}挡着路"
        return [Say("owner", "我请旁边的人帮忙。", "nod"),
                Say("stranger", f"您好，打扰一下！我是导盲犬{self.name}。{problem}，"
                                "我的主人看不见，能麻烦您帮忙挪一下吗？谢谢您！", "look_around")]
