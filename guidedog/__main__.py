"""Try the guide dog on photos.

    python -m guidedog look photo.jpg                     # routine look while walking
    python -m guidedog look photo.jpg --ask "前面有什么？"  # owner asked a question
    python -m guidedog look a.jpg b.jpg --speak           # also play the speech
    python -m guidedog look a.jpg --wav out/              # save the speech as WAV files
"""

import argparse
import os

from .audio import play, to_wav
from .config import load_settings
from .doubao import TTS_SAMPLE_RATE, Doubao
from .guide import Guide
from .perception import look


def main() -> None:
    p = argparse.ArgumentParser(prog="guidedog")
    sub = p.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("look", help="look at photos in order, as if walking")
    lk.add_argument("photos", nargs="+")
    lk.add_argument("--ask", default="", help="the owner's question")
    lk.add_argument("--speak", action="store_true", help="play the speech")
    lk.add_argument("--wav", help="folder to save the speech in")
    args = p.parse_args()

    ai, guide = Doubao(load_settings()), Guide()
    for n, path in enumerate(args.photos):
        print(f"\n[{os.path.basename(path)}]")
        scene = look(ai, open(path, "rb").read(), args.ask)
        for i, s in enumerate(guide.on_scene(scene, asked=bool(args.ask))):
            print(f"  → {s.to} ({s.gesture}): {s.text}")
            if args.speak or args.wav:
                pcm = ai.speak(s.text, "zh")
                if args.wav:
                    os.makedirs(args.wav, exist_ok=True)
                    open(f"{args.wav}/{n:02d}_{i}_{s.to}.wav", "wb").write(to_wav(pcm, TTS_SAMPLE_RATE))
                if args.speak:
                    play(pcm, TTS_SAMPLE_RATE)


if __name__ == "__main__":
    main()
