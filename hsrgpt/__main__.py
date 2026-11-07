"""python -m hsrgpt [--hsr locations.yaml] [--voice]

Without --hsr it drives the simulated household, so you can try the agent on any machine.
"""

from __future__ import annotations

import argparse
import os
import sys

from .agent import Agent
from .robot import SimRobot
from .speech import keyboard_listener, microphone_listener, speaker


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hsrgpt", description="Talk to a Toyota HSR (or a simulated one) through an LLM agent.")
    p.add_argument("--hsr", metavar="LOCATIONS_YAML", help="drive a real HSR; the file names map poses (see locations.example.yaml)")
    p.add_argument("--voice", action="store_true", help="listen on the microphone and speak replies")
    p.add_argument("--wake", default="hey tofu", help="wake phrase in voice mode (default: %(default)s)")
    p.add_argument("--sleep", default="bye", help="phrase that ends a conversation (default: %(default)s)")
    p.add_argument("--model", default=os.environ.get("HSRGPT_MODEL", "gpt-4o-mini"), help="OpenAI model (env HSRGPT_MODEL)")
    p.add_argument("--history", default="history", help="where finished conversations are saved")
    args = p.parse_args(argv)

    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY first.", file=sys.stderr)
        return 1
    from openai import OpenAI

    if args.hsr:
        from .hsr import HSRRobot

        robot = HSRRobot(args.hsr)
    else:
        robot = SimRobot()
        print(f"[sim] places: {', '.join(robot.locations())}. You are in the {robot.user_location}.")

    listen = microphone_listener() if args.voice else keyboard_listener()
    say = speaker(robot, args.voice)
    show_tool = lambda name, a, result: print(f"  · {name}({a}) -> {result}")

    agent: Agent | None = None
    awake = not args.voice  # typing is always "awake"; voice waits for the wake phrase
    if args.voice:
        print(f"[voice] say '{args.wake}' to start, '{args.sleep}' to end.")
    else:
        agent = Agent(robot, OpenAI(), model=args.model, on_tool=show_tool)

    while True:
        heard = listen()
        if heard is None:  # end of input
            break
        if not heard:
            if awake and args.voice:
                say("Sorry, could you say that again?")
            continue
        if not awake:
            if args.wake in heard:
                agent = Agent(robot, OpenAI(), model=args.model, on_tool=show_tool)
                awake = True
                say("Hi! What can I do for you?")
            continue
        if heard.rstrip(".!") == args.sleep:
            say("Bye! Call me if you need anything.")
            if agent and len(agent.messages) > 1:
                print(f"[saved {agent.save(args.history)}]")
            if not args.voice:
                break
            awake, agent = False, None
            continue
        assert agent is not None
        say(agent.chat(heard))

    if agent and len(agent.messages) > 1:
        print(f"[saved {agent.save(args.history)}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
