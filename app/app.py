from tools import recognize_speech
from agents import main

if __name__=="__main__":
    command = recognize_speech()
    if command:
        main(command)
    else:
        print("We ran into some error")