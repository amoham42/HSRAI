import Constants
import recorder
from Assistant import Conversation
import tmc_talk_hoya_py
import time

speaker = tmc_talk_hoya_py.VoiceTextSpeaker(voice='julie')


respond = False


while True:


    # Recorder trascript
    print("initialize")
    user = recorder.record()
    print(user)
    # Wake-up call
    if user == Constants.ENGAGE:
        agent = Conversation()
        respond = True
        dur = speaker.speak("Hello")
    elif user == Constants.DISENGAGE:
        agent.store_history()
        dur = speaker.speak("Bye")
        respond = False
        
    # Respond
    if respond == True:
        text = agent.chat(user)
        print(text)
        dur = speaker.speak(text)
        time.sleep(dur)

        

    

 

