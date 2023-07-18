import Constants
import recorder
from Assistant import Conversation


respond = False


while True:

    # Wake-up call
    if user == Constants.ENGAGE:
        agent = Conversation()
        respond = True
        print("Hello!!")
    elif user == Constants.DISENGAGE:
        agent.store_history()
        print("Bye Bye.")
        respond = False
        

    # Recorder trascript
    user = recorder.record()

    # Respond
    if respond == True:
        text = agent.chat(user)
        print(text)


        

    

 

