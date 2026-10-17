#!/bin/bash
# Run a command in the ROS 2 env (RoboStack pixi in ~/rp1-ros) with the Vbot messages (~/vbot_ws) sourced.
#   scripts/ros.sh python -m guidedog talk --vbot --text
#   scripts/ros.sh ros2 service list -t
# Set RMW_IMPLEMENTATION=rmw_zenoh_cpp (and Zenoh settings) when connecting to the real dog if it uses Zenoh.
cd "$(dirname "$0")/.." || exit 1
exec ~/.pixi/bin/pixi run --manifest-path ~/rp1-ros/pixi.toml bash -c \
  'source ~/vbot_ws/install/setup.bash && export PYTHONPATH="$PWD:$PYTHONPATH" && exec "$@"' _ "$@"
