"""The conversation loop: the model talks, calls robot tools, sees their results, and repeats until
it has something to say back."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .robot import Robot
from .tools import run_tool, tool_schemas

SYSTEM_PROMPT = """\
You are Toyota's Human Support Robot (HSR), a friendly home-assistant robot with a wheeled base,
an arm with a gripper, and a head camera. You talk with people out loud, so:
- Answer in one to three short spoken sentences, with a light touch of humour. No lists, no markdown.
- When asked to do something physical, use your tools. Plan the steps yourself: look before you
  pick, go to the user before handing something over.
- Never claim to have done something a tool didn't confirm. If a tool reports an error, adapt or
  explain simply what went wrong.
- You can only do what your tools allow. Say so plainly when asked for anything else.
"""


@dataclass
class Agent:
    robot: Robot
    client: Any  # openai.OpenAI, or anything with the same chat.completions.create
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_steps: int = 12  # tool rounds per user turn, so a confused model can't loop forever
    on_tool: Callable[[str, str, str], None] | None = None  # (name, arguments, result), for logging/UI
    messages: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._tools = tool_schemas(self.robot)

    def chat(self, text: str) -> str:
        """One user turn: returns what the robot says back."""
        self.messages.append({"role": "user", "content": text})
        for _ in range(self.max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self._tools,
                temperature=self.temperature,
            )
            message = response.choices[0].message
            calls = message.tool_calls or []
            self.messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    **(
                        {
                            "tool_calls": [
                                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                for c in calls
                            ]
                        }
                        if calls
                        else {}
                    ),
                }
            )
            if not calls:
                return message.content or ""
            for call in calls:
                result = run_tool(self.robot, call.function.name, call.function.arguments)
                if self.on_tool:
                    self.on_tool(call.function.name, call.function.arguments, result)
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        reply = "Sorry, I got a bit tangled up planning that. Could you say it another way?"
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def save(self, directory: str | Path = "history") -> Path:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        out = path / f"conversation_{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
        out.write_text(json.dumps(self.messages, indent=2))
        return out
