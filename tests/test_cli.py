"""The command-line loop in keyboard mode, with the OpenAI client swapped for a script."""

import io
import sys
from types import SimpleNamespace as NS

import openai

from hsrgpt.__main__ import main


def test_keyboard_session(monkeypatch, tmp_path, capsys):
    replies = iter(["Hello there!", "On my way out, then."])
    fake = NS(chat=NS(completions=NS(create=lambda **_: NS(choices=[NS(message=NS(content=next(replies), tool_calls=None))]))))
    monkeypatch.setattr(openai, "OpenAI", lambda: fake)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(sys, "stdin", io.StringIO("hi\nhow are you\nbye\n"))

    assert main(["--history", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "robot> Hello there!" in out and "robot> Bye!" in out
    assert len(list(tmp_path.glob("conversation_*.json"))) == 1


def test_needs_an_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main([]) == 1
