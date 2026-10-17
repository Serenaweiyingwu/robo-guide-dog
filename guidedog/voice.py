"""What the owner says to Kiki: a wake word, then a command or a question.

Commands are matched locally (no network) so "停" works instantly; anything else is a question for the camera.
"""

import re
from dataclasses import dataclass

# Speech recognition writes "Kiki" in many ways in Chinese.
WAKE = re.compile(r"^\W*(嘿\W*|hey\W+)?(kiki|琪琪|奇奇|七七|淇淇|琦琦|齐齐|棋棋|key\s*key)\W*", re.I)

# Checked in order; the first match wins, so "停" beats everything.
COMMANDS = [
    ("stop", r"停|别动|站住|不要走"),
    ("follow", r"跟着我|跟我走|走吧|出发|继续走"),
    ("quiet", r"安静|少说|别说了|闭嘴"),
    ("chatty", r"多说|一边走一边说|随时告诉我"),
    ("repeat", r"再说一遍|重复|没听清"),
    ("ask_help", r"请人帮忙|找人帮忙|叫人帮忙|请.*挪"),
]


@dataclass
class Heard:
    kind: str  # stop, follow, quiet, chatty, repeat, ask_help, look (a question), none (not for Kiki)
    text: str = ""  # the question, for "look"


def parse(utterance: str) -> Heard:
    m = WAKE.match(utterance or "")
    if not m:
        return Heard("none")
    rest = utterance[m.end():].strip()
    for kind, pattern in COMMANDS:
        if re.search(pattern, rest):
            return Heard(kind)
    return Heard("look", rest or "前面有什么？")
