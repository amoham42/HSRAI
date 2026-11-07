"""Toyota Human Support Robot backend, through Toyota's `hsrb_interface` Python API.

Needs the HSR's ROS environment (the robot itself or its Gazebo simulator) and a `locations.yaml`
naming map poses. Navigation, relative base motion, head and arm poses, the gripper and speech
are driven directly. Object detection and grasp planning depend on the perception stack a lab
runs, so they are left to `perception` (see `Perception` below); without one, the agent is
told those tools are unavailable and plans around them.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

import yaml

from .robot import Robot, RobotError

HEAD_POSES = {  # (pan, tilt) in radians
    "forward": (0.0, 0.0),
    "down": (0.0, -0.6),
    "up": (0.0, 0.3),
    "left": (0.8, 0.0),
    "right": (-0.8, 0.0),
}


class Perception(Protocol):
    """Plug in a lab's detector / grasp planner."""

    def find_objects(self, robot: "HSRRobot") -> list[str]: ...

    def pick(self, robot: "HSRRobot", obj: str) -> None: ...


class HSRRobot(Robot):
    def __init__(self, locations_file: str | Path, perception: Perception | None = None, timeout: float = 60.0):
        import hsrb_interface  # only available on the robot / in its ROS workspace

        with open(locations_file) as f:
            self._locations: dict[str, list[float]] = {k.lower(): v for k, v in yaml.safe_load(f).items()}
        self._robot = hsrb_interface.Robot()
        self.base = self._robot.get("omni_base")
        self.body = self._robot.get("whole_body")
        self.gripper = self._robot.get("gripper")
        self.tts = self._robot.get("default_tts")
        self.tts.language = self.tts.ENGLISH
        self.perception = perception
        self.timeout = timeout
        self.holding: str | None = None
        self.location = "unknown"

    def locations(self) -> list[str]:
        return list(self._locations)

    def go_to(self, location: str) -> str:
        name = location.strip().lower()
        if name not in self._locations:
            raise RobotError(f"unknown location '{location}'. Known: {', '.join(self._locations)}")
        x, y, yaw_deg = self._locations[name]
        self.body.move_to_go()  # tuck the arm before driving
        try:
            self.base.go_abs(x, y, math.radians(yaw_deg), self.timeout)
        except Exception as e:  # hsrb_interface raises on timeouts and planner failures
            raise RobotError(f"could not reach the {name}: {e}") from e
        self.location = name
        return f"arrived at the {name}"

    def move(self, forward_m: float = 0.0, left_m: float = 0.0, turn_deg: float = 0.0) -> str:
        if max(abs(forward_m), abs(left_m)) > 2.0:
            raise RobotError("relative moves are limited to 2 m; use go_to for longer trips")
        try:
            self.base.go_rel(forward_m, left_m, math.radians(turn_deg), self.timeout)
        except Exception as e:
            raise RobotError(f"move failed: {e}") from e
        return f"moved {forward_m:+.2f} m forward, {left_m:+.2f} m left, turned {turn_deg:+.0f}°"

    def look(self, direction: str) -> str:
        if direction not in HEAD_POSES:
            raise RobotError(f"direction must be one of {', '.join(HEAD_POSES)}")
        pan, tilt = HEAD_POSES[direction]
        self.body.move_to_joint_positions({"head_pan_joint": pan, "head_tilt_joint": tilt})
        return f"looking {direction}"

    def find_objects(self) -> list[str]:
        if not self.perception:
            return super().find_objects()
        return self.perception.find_objects(self)

    def pick(self, obj: str) -> str:
        if not self.perception:
            return super().pick(obj)
        if self.holding:
            raise RobotError(f"already holding the {self.holding}")
        self.gripper.command(1.0)  # open
        self.perception.pick(self, obj)
        self.holding = obj
        return f"picked up the {obj}"

    def place(self) -> str:
        if not self.holding:
            raise RobotError("not holding anything")
        self.body.move_to_neutral()
        self.gripper.command(1.0)
        obj, self.holding = self.holding, None
        self.body.move_to_go()
        return f"put the {obj} down"

    def hand_over(self) -> str:
        if not self.holding:
            raise RobotError("not holding anything")
        self.body.move_to_neutral()  # arm forward, at a comfortable height to take from
        self.say(f"Here is the {self.holding}.")
        self.gripper.command(1.0)
        obj, self.holding = self.holding, None
        self.body.move_to_go()
        return f"handed the {obj} over"

    def status(self) -> str:
        held = f"holding the {self.holding}" if self.holding else "hands empty"
        return f"at {self.location}, {held}"

    def say(self, text: str) -> None:
        self.tts.say(text)
