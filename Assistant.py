from datetime import datetime
import Constants
import openai
import json

class Conversation:
    def __init__(self):
        self.openai.api_key = open(Constants.API_KEY_PATH, "r").read().strip('\n')
        self.message_history = [{"role": "user", "content": open(Constants.PROMPT_PATH, "r").read().strip('\n')}, {"role": "assistant", "content": f"OK"}]
        
    def chat(self, input, role = "user"):
        self.message_history.append({"role": role, "content": input})

        completion = openai.ChatCompletion.create(
            model = Constants.MODEL_ID,
            messages = self.message_history,
            temperature = Constants.TEMPERATURE
        )
    
        reply = completion.choices[0].message.content
        self.message_history.append({"role": "assistant", "content": reply})
        return reply
    

    def store_history(self):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') # Current time

        # Store Json in path
        with open(f"{Constants.HISTORY_PATH}agent_{timestamp}.json", 'w') as f:
            json.dump(self.message_history, f, indent=4)
