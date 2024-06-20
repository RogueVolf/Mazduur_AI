import speech_recognition as sr
import pyttsx3
from groq import Groq
from typing_extensions import Annotated
from dotenv import load_dotenv
import os

env_path = "D:/ABRAR/1_PERSONAL/Wolf_Tech/Mazduur_AI/app/.env"
load_dotenv(env_path)

#Tool to get response from an llm
def use_llm(message: Annotated[str, "The message for the llm"]) -> Annotated[str, "The response from the llm"]:
    """
    Use LLM to complete a particular task

    Returns:
        str: The LLM's response to the given task
    """
    
    client = Groq(
        api_key=os.environ["GROQ_KEY"],
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
        model="llama3-8b-8192",
    )
    response = chat_completion.choices[0].message.content

    return response

# Tool to get response from an llm


def use_llm_naked(system_message: Annotated[str,"The system message for the llm"],
                  message: Annotated[str, "The message for the llm"]
                  ) -> Annotated[str, "The response from the llm"]:
    """
    Use LLM to complete a particular task

    Returns:
        str: The LLM's response to the given task
    """

    client = Groq(
        api_key=os.environ["GROQ_KEY"],
    )
    messages = [
        {
            'role': 'system',
            'content': system_message
        },
        {
            'role': 'user',
            'content': message
        }
    ]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-8b-8192",
    )
    response = chat_completion.choices[0].message.content

    return response


# Function to convert text to speech
def speak_text(command:Annotated[str,"The text to convert to speech"]) -> None:
    # Initialize the engine
    engine = pyttsx3.init()
    
    voices = engine.getProperty('voices')  # getting details of current voice
    # changing index, changes voices. 1 for female 0 for male
    engine.setProperty('voice', voices[0].id)


    # getting details of current speaking rate
    rate = engine.getProperty('rate')
    engine.setProperty('rate', 175)     # setting up new voice rate, default is 200
    
    engine.say(command)
    engine.runAndWait()
    return


# Function to convert text to speech
def recognize_speech() -> Annotated[str, "Returns the user spoken command"]:
    recog = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            # adjust for ambient noise
            recog.adjust_for_ambient_noise(source, duration=0.2)

            speak_text("Start speaking now")
            # listen to user
            audio = recog.listen(source)

            # using Google to recognize spoken command
            command = recog.recognize_google(audio, language="en-IN")

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
