"""The robot's abilities as OpenAI function-calling tools, and the dispatcher that runs them."""

from __future__ import annotations

import json
from typing import Any

from .robot import Robot, RobotError


def _fn(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


def tool_schemas(robot: Robot) -> list[dict]:
    places = robot.locations()
    return [
        _fn(
            "go_to",
            "Drive to a named place. Use 'user' for wherever the person you are talking to is.",
            {"location": {"type": "string", "description": f"one of: {', '.join(places)}, or 'user'"}},
            ["location"],
        ),
        _fn(
            "move",
            "Small relative base motion, for fine positioning (at most 2 m).",
            {
                "forward_m": {"type": "number", "description": "metres forward (negative = back)"},
                "left_m": {"type": "number", "description": "metres to the left (negative = right)"},
                "turn_deg": {"type": "number", "description": "degrees counter-clockwise"},
            },
        ),
        _fn(
            "look",
            "Point the head camera.",
            {"direction": {"type": "string", "enum": ["forward", "down", "up", "left", "right"]}},
            ["direction"],
        ),
        _fn("find_objects", "Look around the current place and list the objects you can see."),
        _fn(
            "pick",
            "Pick up an object that find_objects reported here. You can hold one object at a time.",
            {"object": {"type": "string"}},
            ["object"],
        ),
        _fn("place", "Put the held object down here."),
        _fn("hand_over", "Hand the held object to the user (you must be where the user is)."),
        _fn("status", "Where you are and what you are holding."),
    ]


def run_tool(robot: Robot, name: str, arguments: str) -> str:
    """Runs one tool call. Always returns text for the model, even when the call fails."""
    try:
        args: dict[str, Any] = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "error: arguments were not valid JSON"
    try:
        if name == "go_to":
            return robot.go_to(str(args["location"]))
        if name == "move":
            return robot.move(
                float(args.get("forward_m", 0.0)), float(args.get("left_m", 0.0)), float(args.get("turn_deg", 0.0))
            )
        if name == "look":
            return robot.look(str(args["direction"]))
        if name == "find_objects":
            found = robot.find_objects()
            return "I see: " + ", ".join(found) if found else "I don't see any objects here"
        if name == "pick":
            return robot.pick(str(args["object"]))
        if name == "place":
            return robot.place()
        if name == "hand_over":
            return robot.hand_over()
        if name == "status":
            return robot.status()
        return f"error: unknown tool {name}"
    except KeyError as e:
        return f"error: missing argument {e}"
    except RobotError as e:
        return f"error: {e}"
