# HSRGPT

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

Talk to Toyota's **Human Support Robot** and have it act on what you say. HSRGPT connects a large language model to the HSR through **function calling**: the model chats with you, decides which robot actions a request needs, calls them, reads back what happened, and keeps going until the job is done. Then it tells you, out loud.

```
you> could you bring me the cup?
  · go_to({"location": "kitchen"}) -> arrived at the kitchen
  · find_objects({}) -> I see: cup, apple, water bottle
  · pick({"object": "cup"}) -> picked up the cup
  · go_to({"location": "user"}) -> arrived at the living room
  · hand_over({}) -> handed the cup to the user
robot> Here's your cup, freshly delivered!
```

*(This is the output format, shown with the built-in simulator. The same tool sequence is checked in `tests/test_agent.py`.)*

I started this during my internship at MassRobotics, building demo applications for the HSR.

## How it works

```
 microphone ──► speech-to-text ──► Agent ──► LLM (tools: go_to, move, look, find_objects,
                                     ▲  │                   pick, place, hand_over, status)
                                     │  ▼
                         tool result ◄── Robot ──► SimRobot  (any machine, used by the tests)
                                              └──► HSRRobot  (hsrb_interface on the real HSR)
 speaker ◄── HSR voice / pyttsx3 ◄── reply
```

- **`hsrgpt/agent.py`** runs the loop. It sends the conversation and the tool list to the model, executes any tool calls, appends each result, and repeats. It is capped at 12 tool rounds per turn so a confused model can't loop forever. Conversations are saved as JSON.
- **`hsrgpt/tools.py`** defines the robot's abilities as JSON-schema tools. The `go_to` description lists the robot's real places. Bad arguments and failed actions come back to the model as `error: …` text, never exceptions, so the model can recover. For example, it learns to look before it picks.
- **`hsrgpt/robot.py`** holds the `Robot` interface and `SimRobot`, a small household with rooms, objects and one gripper. Its rules are strict on purpose: the robot must look before picking, can hold one thing at a time, and must be beside you to hand something over. That makes the model plan.
- **`hsrgpt/hsr.py`** is the real robot, driven through Toyota's `hsrb_interface`:
  - navigation to named map poses (`omni_base.go_abs`), plus relative moves
  - head pan and tilt
  - arm poses (`move_to_go`, `move_to_neutral`)
  - the gripper
  - the HSR's own text-to-speech

  Object detection and grasp planning depend on the perception stack each lab runs, so they plug in through a small `Perception` interface. Without one, the model is told those tools are unavailable.
- **`hsrgpt/speech.py`** handles voice. Speech-to-text comes from SpeechRecognition. Replies go out through the HSR's voice when it has one, otherwise pyttsx3. In voice mode a wake phrase starts a conversation ("hey tofu") and "bye" ends it.

## Run it

```sh
git clone https://github.com/amoham42/HSRAI.git && cd HSRAI
pip install -e .                      # keyboard mode and the real-HSR backend
pip install -e ".[voice]"             # add microphone input and spoken replies
export OPENAI_API_KEY=sk-...          # never commit it; see .gitignore

hsrgpt                                # type to the simulated robot
hsrgpt --voice                        # talk to it (needs a microphone)
hsrgpt --hsr locations.yaml --voice   # the real HSR, from its ROS environment
```

`python -m hsrgpt` works the same as `hsrgpt`. Editable installs need pip 21.3 or newer (`python -m pip install -U pip`). On Linux, `pyaudio` builds against PortAudio, so install `portaudio19-dev` first.

On the robot, copy `locations.example.yaml` to `locations.yaml` and fill in map poses for your rooms. Choose the model with `--model` or `HSRGPT_MODEL`.

Python 3.8 is the minimum because ROS Noetic (Ubuntu 20.04), the ROS 1 release current HSR software targets, ships Python 3.8. The tests pass on 3.8, 3.9, 3.11 and 3.13. The `hsr.py` backend has **not been tested on a real HSR** yet; everything else is covered by the simulator and the tests below.

## Tests

```sh
pip install -e ".[dev]"
pytest                    # no network or API key needed
ruff check . && ruff format --check .
mypy
```

The tests replace the OpenAI client with a scripted one. They cover:
- a full fetch-and-deliver task
- errors flowing back to the model
- the step limit
- argument validation
- conversation saving
- the keyboard CLI

## Safety

This drives a real robot. Keep the emergency stop within reach, run the HSR's own safety checks first, and clear the space it moves in. The relative-move tool is capped at 2 m. Longer trips go through the HSR's navigation stack, which plans around obstacles.

## License

[MIT](LICENSE) © 2023 Arman Mohammadi
