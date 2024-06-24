import os
import sys
from groq import Groq
from typing_extensions import Annotated
from dotenv import load_dotenv

load_dotenv('.env')

def get_base_path():
    if getattr(sys, 'frozen', False):
        # The application is bundled
        return sys._MEIPASS
    else:
        # The application is not bundled
        return os.path.dirname(os.path.abspath(__file__))


def get_database_url():
    base_path = get_base_path()
    db_path = os.path.join(base_path, 'db', 'auto_db.sqlite')
    return f"sqlite:///{db_path}"

# Tool to get response from an llm
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
