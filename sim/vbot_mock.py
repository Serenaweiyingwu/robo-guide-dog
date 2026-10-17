"""Stand-in Vbot 大头 for testing Kiki without the robot.

Offers the same message types as the real dog, under made-up names (Kiki finds them by type).
Change the world while it runs:
    ros2 param set /vbot_mock front_m 0.8      # obstacle distance ahead
    ros2 param set /vbot_mock step_m -0.12     # step/drop 1 m ahead (0 = flat)
    ros2 param set /vbot_mock doa_deg 90       # someone said "大头大头" from the right
Speech that reaches the "speaker" is saved to <out>/spoken_NN.wav.

Run (ROS 2 env with ~/vbot_ws sourced):  python sim/vbot_mock.py testdata/wikimedia/*.jpg
"""

import itertools
import os
import sys
import time
import wave

import rclpy
from camera_msgs.msg import JpegResponse
from camera_msgs.srv import GetJpegImages
from function_msgs.msg import AgentToSpeechAudioRaw
from function_msgs.srv import BaseAction, ControlFollowing
from lowlevel_msg.msg import HeadCmd, HeightMap, SportModeState
from rclpy.node import Node
from speech_msgs.msg import WakeupInfo


class MockVbot(Node):
    def __init__(self, photos, out):
        super().__init__("vbot_mock")
        self.photos, self.out = itertools.cycle(photos), out
        os.makedirs(out, exist_ok=True)
        self.declare_parameter("front_m", 5.0)
        self.declare_parameter("step_m", 0.0)
        self.declare_parameter("doa_deg", -1)
        self.audio, self.audio_seq, self.last_audio, self.utterances = [], -1, 0.0, 0
        self.following = False
        self.create_service(GetJpegImages, "/mock/camera/get_jpeg", self.on_camera)
        self.create_service(ControlFollowing, "/mock/function/following", self.on_follow)
        self.create_service(BaseAction, "/mock/function/base_action", self.on_action)
        self.create_subscription(AgentToSpeechAudioRaw, "/mock/agent/audio_raw", self.on_audio, 50)
        self.create_subscription(HeadCmd, "/mock/head/cmd", self.on_head, 10)
        self.state = self.create_publisher(SportModeState, "/mock/sport/state", 10)
        self.hmap = self.create_publisher(HeightMap, "/mock/perception/heightmap", 1)
        self.wake = self.create_publisher(WakeupInfo, "/mock/speech/wakeup", 10)
        self.create_timer(0.1, self.publish_state)
        self.create_timer(0.5, self.publish_heightmap)
        self.create_timer(0.2, self.flush_audio)
        self.add_on_set_parameters_callback(self.on_param)
        self.get_logger().info("mock Vbot ready")

    def on_param(self, params):
        from rcl_interfaces.msg import SetParametersResult

        for p in params:
            self.get_logger().info(f"world: {p.name} = {p.value}")
            if p.name == "doa_deg" and p.value >= 0:
                self.wake.publish(WakeupInfo(wakeup_source=0, doa_angle=int(p.value), wakeup_word="大头大头"))
        return SetParametersResult(successful=True)

    def on_camera(self, req, res):
        path = next(self.photos)
        res.response = [JpegResponse(status=0, width=1024, height=768, data=list(open(path, "rb").read()))]
        self.get_logger().info(f"camera: {os.path.basename(path)}")
        return res

    def on_follow(self, req, res):
        self.following = req.mode != ControlFollowing.Request.STOP
        res.success, res.message = True, "following" if self.following else "stopped"
        self.get_logger().info(f"follow: mode={req.mode} -> {res.message}")
        return res

    def on_action(self, req, res):
        if req.mode == BaseAction.Request.ROTATE_IN_PLACE:
            self.get_logger().info(f"rotate in place {req.angle_rad * 57.3:+.0f}°")
        else:
            self.get_logger().info(f"base action mode {req.mode}")
        res.success, res.message = True, "ok"
        return res

    def on_head(self, msg):
        self.get_logger().info(f"head pitch={msg.pitch_deg:+.0f} yaw={msg.yaw_deg:+.0f} ({msg.cost_time_ms} ms)")

    def on_audio(self, msg):
        if msg.frame_sequence == 0 and self.audio:
            self.flush_audio(force=True)
        self.audio.extend(msg.audio_data)
        self.last_audio = time.time()

    def flush_audio(self, force=False):
        """Save an utterance once frames stop arriving."""
        if self.audio and (force or time.time() - self.last_audio > 0.6):
            path = f"{self.out}/spoken_{self.utterances:02d}.wav"
            with wave.open(path, "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
                w.writeframes(bytes(memoryview(__import__("array").array("h", self.audio))))
            self.get_logger().info(f"speaker: {len(self.audio) / 16000:.1f}s of speech -> {os.path.basename(path)}")
            self.audio, self.utterances = [], self.utterances + 1

    def publish_state(self):
        m = SportModeState()
        m.range_obstacle = [float(self.get_parameter("front_m").value), 5.0, 5.0, 5.0]
        m.position = [0.0, 0.0, 0.0]
        self.state.publish(m)

    def publish_heightmap(self):
        step, size, res = float(self.get_parameter("step_m").value), 40, 0.1
        m = HeightMap(resolution=res, width=size, height=size, origin=[-2.0, -2.0])
        m.data = [step if ix * res - 2.0 >= 1.0 else 0.0 for iy in range(size) for ix in range(size)]
        self.hmap.publish(m)


def main():
    rclpy.init()
    rclpy.spin(MockVbot(sys.argv[1:] or ["testdata/wikimedia/blocked_bikes_1.jpg"], "testdata/mock_speaker"))


if __name__ == "__main__":
    main()
