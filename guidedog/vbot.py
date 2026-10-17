"""Kiki's body on the 维他动力 Vbot 大头, over ROS 2 (types from github.com/VitaDynamics/vbot_ros2_msgs).

Topic and service *names* aren't documented, so each interface is found by its *type* on the ROS graph.
If a type appears under several names, set the name explicitly, e.g.
    VBOT_SPEAKER=/agent/speech_audio_raw  VBOT_BASE_ACTION=/function/base_action
Things the docs don't say are marked GUESS; check them on the robot.

Runs in the ROS 2 env (pixi in ~/rp1-ros with ~/vbot_ws sourced), not the plain .venv. See scripts/kiki.sh.
"""

import math
import os
import threading
import time
import uuid

import numpy as np
import rclpy
from camera_msgs.msg import JpegRequest
from camera_msgs.srv import GetJpegImages
from function_msgs.msg import AgentToSpeechAudioRaw
from function_msgs.srv import BaseAction, ControlFollowing
from lowlevel_msg.msg import HeadCmd, HeightMap, SportModeState
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from speech_msgs.msg import WakeupInfo

from .obstacles import terrain_ahead

SPEAKER_RATE = 16000  # AgentToSpeechAudioRaw is fixed at 16 kHz mono int16
FRAME = 1600  # 100 ms of audio per message

# (env var, kind, type) for everything Kiki uses
INTERFACES = {
    "speaker": ("VBOT_SPEAKER", "topic", "function_msgs/msg/AgentToSpeechAudioRaw"),
    "head": ("VBOT_HEAD", "topic", "lowlevel_msg/msg/HeadCmd"),
    "state": ("VBOT_STATE", "topic", "lowlevel_msg/msg/SportModeState"),
    "heightmap": ("VBOT_HEIGHTMAP", "topic", "lowlevel_msg/msg/HeightMap"),
    "wakeup": ("VBOT_WAKEUP", "topic", "speech_msgs/msg/WakeupInfo"),
    "camera": ("VBOT_CAMERA", "service", "camera_msgs/srv/GetJpegImages"),
    "follow": ("VBOT_FOLLOW", "service", "function_msgs/srv/ControlFollowing"),
    "base_action": ("VBOT_BASE_ACTION", "service", "function_msgs/srv/BaseAction"),
}

# GUESSES until confirmed on the robot
FRONT_INDEX = int(os.environ.get("VBOT_FRONT_INDEX", "0"))  # which range_obstacle value is "front"
CAMERA_CHANNEL = int(os.environ.get("VBOT_CAMERA_CHANNEL", "0"))  # front camera channel_id
STRANGER_TURN = math.radians(float(os.environ.get("VBOT_STRANGER_TURN_DEG", "45")))  # if no voice direction

# head moves for gestures: list of (pitch_deg, yaw_deg, ms)
HEAD_MOVES = {
    "nod": [(15, 0, 250), (0, 0, 250)],
    "alert": [(-10, 0, 200)],
    "look_around": [(0, 25, 400), (0, -25, 600), (0, 0, 300)],
    "happy": [(10, 0, 150), (0, 0, 150), (10, 0, 150), (0, 0, 150)],
    "listen": [(-5, 0, 300)],
}


class Vbot(Node):
    def __init__(self, log=print, discover_s=5.0):
        super().__init__("kiki_guide_dog")
        self.log = log
        self.names = self._discover(discover_s)
        self.speaker = self.create_publisher(AgentToSpeechAudioRaw, self.names["speaker"], 10)
        self.head = self.create_publisher(HeadCmd, self.names["head"], 10)
        self.camera = self.create_client(GetJpegImages, self.names["camera"])
        self.follow_srv = self.create_client(ControlFollowing, self.names["follow"])
        self.action = self.create_client(BaseAction, self.names["base_action"])
        self.front_m, self.pose, self.heightmap, self.doa = None, None, None, None
        self.create_subscription(SportModeState, self.names["state"], self._on_state, 10)
        self.create_subscription(HeightMap, self.names["heightmap"], self._on_heightmap, 1)
        self.create_subscription(WakeupInfo, self.names["wakeup"], self._on_wakeup, 10)
        self.executor_ = MultiThreadedExecutor()
        self.executor_.add_node(self)
        threading.Thread(target=self.executor_.spin, daemon=True).start()

    # ---- discovery ----

    def _discover(self, seconds):
        """Map each interface to a name: env override, else the only name with that type on the graph."""
        names, deadline = {}, time.time() + seconds
        while True:
            topics = self.get_topic_names_and_types()
            services = self.get_service_names_and_types()
            missing = []
            for key, (env, kind, typ) in INTERFACES.items():
                if os.environ.get(env):
                    names[key] = os.environ[env]
                    continue
                found = [n for n, types in (topics if kind == "topic" else services) if typ in types]
                if len(found) == 1:
                    names[key] = found[0]
                elif len(found) > 1:
                    raise RuntimeError(f"{typ} is offered as {found}; set {env} to choose one")
                else:
                    missing.append(key)
            if not missing or time.time() > deadline:
                break
            time.sleep(0.5)
        for key in missing:  # not on the graph (yet): fall back to a placeholder so the rest still works
            names[key] = f"/kiki_unconnected/{key}"
            self.log(f"  [vbot] WARNING: no {INTERFACES[key][2]} found ({key}); set {INTERFACES[key][0]}")
        for key, name in names.items():
            self.log(f"  [vbot] {key:12s} -> {name}")
        return names

    # ---- sensors ----

    def _on_state(self, msg):
        self.front_m = float(msg.range_obstacle[FRONT_INDEX])
        self.pose = (msg.position[0], msg.position[1], msg.imu_state.rpy[2])  # x, y, yaw (GUESS: same frame as map)

    def _on_heightmap(self, msg):
        self.heightmap = msg

    def _on_wakeup(self, msg):
        if msg.doa_angle >= 0:
            self.doa = (time.time(), msg.doa_angle)

    def terrain(self):
        m, p = self.heightmap, self.pose
        if m is None or p is None:
            return None
        return terrain_ahead(list(m.data), m.width, m.height, m.resolution, tuple(m.origin), (p[0], p[1]), p[2])

    # ---- calls ----

    def call(self, client, request, timeout=5.0):
        if not client.wait_for_service(timeout_sec=timeout):
            raise RuntimeError(f"service {client.srv_name} not available")
        future = client.call_async(request)
        end = time.time() + timeout
        while not future.done() and time.time() < end:
            time.sleep(0.02)
        if not future.done():
            raise RuntimeError(f"service {client.srv_name} timed out")
        return future.result()


class VbotCamera:
    def __init__(self, vbot: Vbot):
        self.vbot = vbot

    def snap(self) -> bytes:
        req = GetJpegImages.Request()
        req.request = [JpegRequest(channel_id=CAMERA_CHANNEL, width=1280, height=720, quality=80, undistort=True)]
        res = self.vbot.call(self.vbot.camera, req)
        if not res.response or res.response[0].status != 0 or not res.response[0].data:
            raise RuntimeError(f"camera returned no image (status {res.response[0].status if res.response else 'none'})")
        return bytes(res.response[0].data)


class VbotBody:
    rate = SPEAKER_RATE

    def __init__(self, vbot: Vbot, log=print):
        self.vbot, self.log = vbot, log
        self.turned = 0.0  # how far we turned away from the owner, to turn back
        self.cut = threading.Event()

    def interrupt(self) -> None:
        """Stop streaming the current speech (an obstacle warning needs the speaker)."""
        self.cut.set()

    def say(self, pcm: bytes, rate: int) -> None:
        """Stream speech to the dog's speaker at roughly real-time pace, returning when it has played."""
        samples = np.frombuffer(pcm, dtype=np.int16)
        self.cut.clear()
        start = time.time()
        for seq, i in enumerate(range(0, len(samples), FRAME)):
            if self.cut.is_set():
                return
            chunk = samples[i:i + FRAME]
            msg = AgentToSpeechAudioRaw(sample_rate=SPEAKER_RATE, num_channels=1, bit_depth=16,
                                        num_samples=len(chunk), frame_sequence=seq, audio_data=chunk.tolist())
            self.vbot.speaker.publish(msg)
            ahead = start + (i + len(chunk)) / SPEAKER_RATE - 0.3  # stay ~300 ms ahead of playback
            time.sleep(max(0.0, ahead - time.time()))
        while time.time() < start + len(samples) / SPEAKER_RATE and not self.cut.is_set():
            time.sleep(0.05)

    def face(self, who: str) -> None:
        if who == "stranger":
            doa = self.vbot.doa
            if doa and time.time() - doa[0] < 20:  # recent voice direction: turn to it (DOA is clockwise)
                angle = -math.radians(((doa[1] + 180) % 360) - 180)
            else:
                angle = STRANGER_TURN
            self._rotate(angle)
            self.turned += angle
        elif who == "owner" and self.turned:
            self._rotate(-self.turned)
            self.turned = 0.0

    def gesture(self, name: str) -> None:
        for pitch, yaw, ms in HEAD_MOVES.get(name, []):
            self.vbot.head.publish(HeadCmd(pitch_deg=float(pitch), yaw_deg=float(yaw), cost_time_ms=ms))
            time.sleep(ms / 1000)

    def stop(self) -> None:
        self._follow(ControlFollowing.Request.STOP)

    def follow(self) -> None:
        self._follow(ControlFollowing.Request.FOLLOWING)

    def _follow(self, mode: int) -> None:
        req = ControlFollowing.Request(target_state=1, mode=mode, req_id=str(uuid.uuid4()))  # GUESS: STOP via mode
        res = self.vbot.call(self.vbot.follow_srv, req)
        self.log(f"  [vbot] follow mode {mode}: {'ok' if res.success else 'FAILED ' + res.message}")

    def _rotate(self, angle: float) -> None:
        req = BaseAction.Request(target_state=1, mode=BaseAction.Request.ROTATE_IN_PLACE,
                                 angle_rad=float(angle), req_id=str(uuid.uuid4()))
        res = self.vbot.call(self.vbot.action, req, timeout=10.0)
        self.log(f"  [vbot] rotate {math.degrees(angle):+.0f}°: {'ok' if res.success else 'FAILED ' + res.message}")


def connect(log=print):
    """Start ROS, find the dog's interfaces, and return (camera, body, vbot)."""
    rclpy.init()
    vbot = Vbot(log=log)
    return VbotCamera(vbot), VbotBody(vbot, log=log), vbot
