"""The agent loop and the simulated robot, with a scripted stand-in for the OpenAI client."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS

import pytest

from hsrgpt import Agent, SimRobot
from hsrgpt.tools import run_tool, tool_schemas


def call(name: str, i: int, **args) -> NS:
    return NS(id=f"call_{i}", function=NS(name=name, arguments=json.dumps(args)))


class ScriptedClient:
    """Replays a fixed list of model turns and records what the agent sent each time."""

    def __init__(self, turns: list[NS]):
        self.turns = list(turns)
        self.requests: list[dict] = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs) -> NS:
        self.requests.append(kwargs)
        return NS(choices=[NS(message=self.turns.pop(0))])


def say(text: str) -> NS:
    return NS(content=text, tool_calls=None)


def act(*calls: NS) -> NS:
    return NS(content=None, tool_calls=list(calls))


def test_fetch_a_cup_end_to_end():
    robot = SimRobot()
    client = ScriptedClient(
        [
            act(call("go_to", 1, location="kitchen")),
            act(call("find_objects", 2)),
            act(call("pick", 3, object="cup")),
            act(call("go_to", 4, location="user"), call("hand_over", 5)),
            say("Here's your cup, freshly delivered!"),
        ]
    )
    agent = Agent(robot, client)
    reply = agent.chat("Could you bring me the cup?")

    assert reply == "Here's your cup, freshly delivered!"
    assert robot.log == [
        "arrived at the kitchen",
        "looked around the kitchen",
        "picked up the cup",
        "arrived at the living room",
        "handed the cup to the user",
    ]
    assert robot.holding is None and "cup" not in robot.world["kitchen"]
    # every tool call got exactly one result, in order, before the next model turn
    tool_msgs = [m for m in agent.messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == [f"call_{i}" for i in range(1, 6)]
    assert "I see: cup, apple, water bottle" in tool_msgs[1]["content"]
    assert all("tools" in r for r in client.requests)


def test_tool_errors_go_back_to_the_model():
    robot = SimRobot()
    client = ScriptedClient(
        [
            act(call("pick", 1, object="cup")),  # hasn't looked, and the cup is in another room
            say("I need to go find it first."),
        ]
    )
    agent = Agent(robot, client)
    agent.chat("pick up the cup")
    result = next(m for m in agent.messages if m["role"] == "tool")["content"]
    assert result.startswith("error:") and "find_objects" in result
    assert robot.holding is None


def test_step_limit_stops_a_looping_model():
    robot = SimRobot()
    client = ScriptedClient([act(call("status", i)) for i in range(20)])
    agent = Agent(robot, client, max_steps=4)
    reply = agent.chat("hmm")
    assert "tangled" in reply
    assert len(client.requests) == 4


def test_history_round_trips(tmp_path):
    agent = Agent(SimRobot(), ScriptedClient([say("Hello!")]))
    agent.chat("hi")
    saved = json.loads(agent.save(tmp_path).read_text())
    assert [m["role"] for m in saved] == ["system", "user", "assistant"]


@pytest.mark.parametrize(
    "name,args,expect",
    [
        ("go_to", {"location": "garage"}, "error: unknown location"),
        ("go_to", {}, "error: missing argument"),
        ("move", {"forward_m": 5}, "error: relative moves are limited"),
        ("look", {"direction": "sideways"}, "error: direction must be"),
        ("place", {}, "error: not holding anything"),
        ("teleport", {}, "error: unknown tool"),
    ],
)
def test_bad_calls_are_reported_not_raised(name, args, expect):
    assert run_tool(SimRobot(), name, json.dumps(args)).startswith(expect)


def test_invalid_json_arguments():
    assert run_tool(SimRobot(), "go_to", "{not json").startswith("error:")


def test_schemas_list_the_robots_places():
    schemas = {s["function"]["name"]: s for s in tool_schemas(SimRobot())}
    assert set(schemas) == {"go_to", "move", "look", "find_objects", "pick", "place", "hand_over", "status"}
    assert "kitchen" in schemas["go_to"]["function"]["parameters"]["properties"]["location"]["description"]


def test_sim_holds_one_thing_at_a_time():
    robot = SimRobot()
    robot.go_to("kitchen")
    robot.find_objects()
    robot.pick("cup")
    with pytest.raises(Exception, match="already holding"):
        robot.pick("apple")
    robot.place()
    assert "cup" in robot.world["kitchen"]
