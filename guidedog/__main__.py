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
    tk = sub.add_parser("talk", help="talk to Kiki; photos stand in for her camera unless --vbot")
    tk.add_argument("photos", nargs="*")
    tk.add_argument("--vbot", action="store_true", help="use the Vbot dog (run via scripts/ros.sh)")
    tk.add_argument("--text", action="store_true", help="type instead of speaking (also: !front 0.8, !step -0.12, !tick)")
    tk.add_argument("--mute", action="store_true")
    args = p.parse_args()

    if args.cmd == "talk":
        return talk(args)

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


def talk(args) -> None:
    from .dog import GuideDog, LaptopBody, PhotoCamera

    ai = Doubao(load_settings())
    if args.vbot:
        from .vbot import connect

        print("Looking for the dog on the ROS network...")
        camera, body, vbot = connect()
    else:
        camera, body, vbot = PhotoCamera(args.photos), LaptopBody(mute=args.mute), None
    kiki = GuideDog(ai, camera, body)
    print("Kiki is waking up...")
    kiki.warm_up()
    if vbot:
        start_sensing(kiki, vbot)
    print('Say "Kiki，前面有什么？" (or 停 / 跟着我 / 安静 / 多说点 / 再说一遍 / 请人帮忙). Ctrl+C quits.')
    if args.text:
        print("Text mode. Simulate sensors with: !front 0.8   !step -0.12   !clear   !tick")
    else:
        from .audio import Mic

        mic = Mic()
        mic.calibrate()
    while True:
        try:
            line = input("> ").strip() if args.text else ai.transcribe(mic.listen(), None)
            if line.startswith("!front"):
                kiki.sense(front_m=float(line.split()[1]))
            elif line.startswith("!step"):
                kiki.sense(terrain=(1.0, float(line.split()[1])))
            elif line == "!clear":
                kiki.sense(front_m=5.0)
            elif line == "!tick":
                kiki.walk_tick()
            elif line:
                kiki.hear(line)
        except (KeyboardInterrupt, EOFError):
            print("\nKiki goes to sleep.")
            return
        except Exception as e:  # keep the dog running through network hiccups
            print(f"  [error] {e}")


def start_sensing(kiki, vbot, hz=5.0):
    """Feed the dog's obstacle distance and height map to Kiki in the background."""
    import threading
    import time

    def loop():
        while True:
            try:
                kiki.sense(front_m=vbot.front_m, terrain=vbot.terrain())
            except Exception as e:
                print(f"  [sensing] {e}")
            time.sleep(1 / hz)

    threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    main()
