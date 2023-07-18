# HSRGPT

An API that allows HSR(Human Support Robot) to take advantage of OpenAI's 
ChatGPT to communicate and use its sensors and actuators to manipulate its surroundings.


# Project Description

- By using the new OpenAI's Function calling feature, 
this project is aiming to be able to control the Human Support Robot (HSR)
Using its Python and ROS APIs. By using the GPT4 model,
Human Support Robot will be able to come across as more friendly, and
easier to command. 

- An easy to use framework.
- Flexible and eay to update with new models.


# Usage

For now controls will be limited to Python API. 
ROS API will be added down the road.

Latest version: Python API with Chatbot.

- `git clone https://github.com/amoham42/HSRGPT.git`
- `cd HSRGPT`
- `pip install -r requirements.txt`
- Open Constants folder and change API_KEY for GPT-4.
- Change the Engage and Disengage words if needed.


# Run

- Fill the Prompt file with no space or new lines with any kind of behaviour needed for HSR.
- Setup HSR and do the safety steps. Turn On the HSR.
- Connect to Wifi with internet connection.
- `Main.py`
- HSR responses' history are stored in Responses folder after shutting down the session.


# Vision

HSRGPT is  building an open-source platform for software developers, and engineers that want to use 
AI in there Robots. The goal of this project is to use OpenAI's newest feature to its best, and make this 
project open-ended so it could also be used for other robots and machines. Thank you.