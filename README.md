# HSRGPT

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
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...          # never commit it; see .gitignore

python -m hsrgpt                      # type to the simulated robot
python -m hsrgpt --voice              # talk to it (needs a microphone)
python -m hsrgpt --hsr locations.yaml --voice   # the real HSR, from its ROS environment
```

On the robot, copy `locations.example.yaml` to `locations.yaml` and fill in map poses for your rooms. Choose the model with `--model` or `HSRGPT_MODEL`.

## Tests

```sh
pip install -r requirements-dev.txt
pytest
```

The tests replace the OpenAI client with a scripted one, so they need no network or API key. They cover:
- a full fetch-and-deliver task
- errors flowing back to the model
- the step limit
- argument validation
- conversation saving
- the keyboard CLI

## Safety

This drives a real robot. Keep the emergency stop within reach, run the HSR's own safety checks first, and clear the space it moves in. The relative-move tool is capped at 2 m. Longer trips go through the HSR's navigation stack, which plans around obstacles.
