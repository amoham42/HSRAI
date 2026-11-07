"""What the language model is allowed to do with a robot.

`Robot` is the interface the tools call. `SimRobot` is a small text-mode world (rooms, objects,
a gripper) that runs anywhere and backs the tests; `hsrgpt.hsr.HSRRobot` drives a real Toyota HSR.
Every action returns a short sentence describing what happened, which goes back to the model as
the tool result. Failures raise `RobotError` with a message the model can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class RobotError(Exception):
    """An action that could not be done. The message is shown to the model."""


class Robot:
    """Capabilities shared by every backend. Override what the hardware can do."""

    def locations(self) -> list[str]:
        raise NotImplementedError

    def go_to(self, location: str) -> str:
        raise NotImplementedError

    def move(self, forward_m: float = 0.0, left_m: float = 0.0, turn_deg: float = 0.0) -> str:
        raise NotImplementedError

    def look(self, direction: str) -> str:
        raise NotImplementedError

    def find_objects(self) -> list[str]:
        raise RobotError("this robot has no object detector configured")

    def pick(self, obj: str) -> str:
        raise RobotError("this robot has no grasp planner configured")

    def place(self) -> str:
        raise RobotError("this robot cannot place objects")

    def hand_over(self) -> str:
        raise RobotError("this robot cannot hand objects over")

    def status(self) -> str:
        raise NotImplementedError

    def say(self, text: str) -> None:
        print(f"[robot] {text}")


@dataclass
class SimRobot(Robot):
    """A tiny household: named places, objects lying in them, one gripper.

    Deliberately strict, so the agent has to plan: it must be where an object is to pick it up,
    can hold one thing at a time, and must look before it knows what's in a room.
    """

    world: dict[str, list[str]] = field(
        default_factory=lambda: {
            "living room": ["remote", "book"],
            "kitchen": ["cup", "apple", "water bottle"],
            "bedroom": ["phone"],
            "entrance": [],
        }
    )
    user_location: str = "living room"
    location: str = "living room"
    holding: str | None = None
    head: str = "forward"
    log: list[str] = field(default_factory=list)
    _seen: set[str] = field(default_factory=set)

    def _record(self, line: str) -> str:
        self.log.append(line)
        return line

    def locations(self) -> list[str]:
        return list(self.world)

    def go_to(self, location: str) -> str:
        place = location.strip().lower()
        if place in ("user", "me", "person"):
            place = self.user_location
        if place not in self.world:
            raise RobotError(f"unknown location '{location}'. Known: {', '.join(self.world)}")
        self.location = place
        return self._record(f"arrived at the {place}")

    def move(self, forward_m: float = 0.0, left_m: float = 0.0, turn_deg: float = 0.0) -> str:
        if max(abs(forward_m), abs(left_m)) > 2.0:
            raise RobotError("relative moves are limited to 2 m; use go_to for longer trips")
        return self._record(f"moved {forward_m:+.2f} m forward, {left_m:+.2f} m left, turned {turn_deg:+.0f}°")

    def look(self, direction: str) -> str:
        if direction not in ("forward", "down", "up", "left", "right"):
            raise RobotError("direction must be forward, down, up, left or right")
        self.head = direction
        return self._record(f"looking {direction}")

    def find_objects(self) -> list[str]:
        self._seen.add(self.location)
        self._record(f"looked around the {self.location}")
        return list(self.world[self.location])

    def pick(self, obj: str) -> str:
        name = obj.strip().lower()
        if self.holding:
            raise RobotError(f"already holding the {self.holding}; place or hand it over first")
        if self.location not in self._seen:
            raise RobotError("I haven't looked around here yet; call find_objects first")
        if name not in self.world[self.location]:
            raise RobotError(f"there is no {name} in the {self.location}")
        self.world[self.location].remove(name)
        self.holding = name
        return self._record(f"picked up the {name}")

    def place(self) -> str:
        if not self.holding:
            raise RobotError("not holding anything")
        obj, self.holding = self.holding, None
        self.world[self.location].append(obj)
        return self._record(f"put the {obj} down in the {self.location}")

    def hand_over(self) -> str:
        if not self.holding:
            raise RobotError("not holding anything")
        if self.location != self.user_location:
            raise RobotError(f"the user is in the {self.user_location}; go there first")
        obj, self.holding = self.holding, None
        return self._record(f"handed the {obj} to the user")

    def status(self) -> str:
        held = f"holding the {self.holding}" if self.holding else "hands empty"
        return f"in the {self.location}, {held}, head {self.head}"
