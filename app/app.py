from tools import recognize_speech
from agents import main

if __name__=="__main__":
    choice = input("Choose your input type\n1.Type\n2.Speak\n")
    if choice == '1':
        command = input("Enter your command\n")
    else:
        command = recognize_speech()
    if command:
        main(command)
    else:
        print("We ran into some error")