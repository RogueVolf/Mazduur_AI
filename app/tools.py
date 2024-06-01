import speech_recognition as sr
import pyttsx3
from typing_extensions import Annotated

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

