import speech_recognition as sr
import pyttsx3
from groq import Groq
from typing_extensions import Annotated
from dotenv import load_dotenv
import os

env_path = "/home/ubuntu/Abrar/ai_kgwizard/.env"
load_dotenv(env_path)

#Tool to get response from an llm
def use_llm(message: Annotated[str, "The message for the llm"]) -> Annotated[str, "The response from the llm"]:
    """
    Use LLM to complete a particular task

    Returns:
        str: The LLM's response to the given task
    """
    
    client = Groq(
        api_key=os.environ["GROQ_API_KEY"],
    )
    messages = [
        {
            'role': 'system',
            'content': 'You are an assistant for solving NLP and Reasoning tasks, do not give any code in your response'
        },
        {
            'role': 'user',
            'content': message
        }
    ]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
    )
    response = chat_completion.choices[0].message.content

    return response


#Function to convert text to speech
def recognize_speech() -> Annotated[str,"Returns the user spoken command"] :
    recog = sr.Recognizer()
    try:
        with sr.Microphone () as source:
            #adjust for ambient noise
            recog.adjust_for_ambient_noise(source,duration=0.2)
            
            print("Start speaking now")
            #listen to user
            audio = recog.listen(source)

            #using Google to recognize spoken command
            command = recog.recognize_google(audio)

            return command.lower()
    except sr.RequestError as e:
        print("Could not request results; {0}".format(e))
        return False
    
    except sr.UnknownValueError:
        print("unknown error occurred")
        return False
    
    except Exception as e:
        print(f'Exception {e} occured')
        return False
    
# Function to convert text to speech
def speak_text(command:Annotated[str,"The text to convert to speech"]) -> None:
    # Initialize the engine
    engine = pyttsx3.init()
    engine.say(command)
    engine.runAndWait()
    return

