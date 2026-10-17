"""The guide dog's judgement: given what it sees, what to say, to whom, and with which body language."""

from dataclasses import dataclass

from .perception import Scene


@dataclass
class Say:
    to: str  # "owner" or "stranger"
    text: str
    gesture: str = ""  # alert, nod, look_around, happy, ...


class Guide:
    def __init__(self, name: str = "萝卜"):
        self.name = name
        self.asking_for_help = False  # waiting for strangers to clear the blind path

    def on_scene(self, scene: Scene, asked: bool = False) -> list:
        """asked=True when the owner asked a question; otherwise this is a routine look while walking."""
        out = []
        if self.asking_for_help and not scene.blocked:
            self.asking_for_help = False
            out += [Say("stranger", "谢谢您！", "happy"), Say("owner", "盲道通了，可以继续走。", "nod")]
            return out
        if asked or scene.urgent or scene.blocked:
            out.append(Say("owner", scene.description, "alert" if scene.urgent else "nod"))
        if scene.blocked and scene.movable and scene.people_nearby and not self.asking_for_help:
            self.asking_for_help = True
            what = "、".join(scene.blockers) or "东西"
            out.append(Say("owner", "我请旁边的人帮忙挪一下。", "nod"))
            out.append(Say("stranger", f"您好，打扰一下！我是导盲犬{self.name}。盲道被{what}挡住了，"
                                       "我的主人看不见，能麻烦您帮忙挪一下吗？谢谢您！", "look_around"))
        return out
