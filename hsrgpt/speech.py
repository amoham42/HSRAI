"""Listening and speaking. Microphone input via SpeechRecognition; speech out through the robot's
own voice when it has one (HSR), else pyttsx3, else print. Keyboard mode needs neither."""

from __future__ import annotations

from typing import Callable

from .robot import Robot


def keyboard_listener() -> Callable[[], str | None]:
    def listen() -> str | None:
        try:
            return input("you> ").strip()
        except EOFError:
            return None

    return listen


def microphone_listener(energy_threshold: int = 2000, pause_s: float = 0.6) -> Callable[[], str | None]:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = energy_threshold
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = pause_s
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)

    def listen() -> str | None:
        with mic as source:
            audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio).lower().strip()
        except sr.UnknownValueError:
            return ""  # heard something, couldn't make it out
        except sr.RequestError as e:
            print(f"[speech] recognition service error: {e}")
            return ""

    return listen


def speaker(robot: Robot, use_voice: bool) -> Callable[[str], None]:
    if not use_voice:
        return lambda text: print(f"robot> {text}")
    if type(robot).say is not Robot.say:  # the robot has its own voice
        return robot.say
    try:
        import pyttsx3

        engine = pyttsx3.init()

        def say(text: str) -> None:
            print(f"robot> {text}")
            engine.say(text)
            engine.runAndWait()

        return say
    except Exception:
        return lambda text: print(f"robot> {text}")
