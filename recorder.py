import speech_recognition as sr
import Constants


def record():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 247
    recognizer.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as mic:

            recognizer.energy_threshold = Constants.ENERGY_THRESHOLD
            recognizer.adjust_for_ambient_noise(mic, duration=0.2)
            recognizer.pause_threshold = Constants.PAUSE_DURATION
            audio = recognizer.listen(mic)
            text = recognizer.recognize_google(audio)
            text = text.lower()
            return text

    except sr.UnknownValueError:
        text = "Sorry can you please repeat that?"
        return text
