from autogen.agentchat import AssistantAgent,UserProxyAgent
from autogen.agentchat.conversable_agent import logger
from autogen import Agent
from autogen.runtime_logging import logging_enabled, log_event, log_new_agent
from tools import recognize_speech
from dotenv import load_dotenv
from typing_extensions import Annotated,Optional,List,Dict,Union
from typing import Any
import inspect
import pyttsx3
import os

env_path = "D:/ABRAR/1_PERSONAL/Wolf_Tech/Mazduur_AI/app/.env"
load_dotenv(env_path)


config_list = [{"model": "llama3-70b-8192",
                "api_key": os.environ["GROQ_KEY"],
                "base_url": "https://api.groq.com/openai/v1",
                "max_retries": 10}]

llm_config = {"config_list":config_list,"temperature":0.75,"cache_seed":None}


class ListeningUser(UserProxyAgent):
    def get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        

        reply = recognize_speech()
        self._human_input.append(reply)
        return reply


class SpeakingAssistant(AssistantAgent):
    # Function to convert text to speech
    def SpeakText(self,command):
        # Initialize the engine
        engine = pyttsx3.init()
        engine.say(command)
        engine.runAndWait()

    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        """Reply based on the conversation history and the sender.

        Either messages or sender must be provided.
        Register a reply_func with `None` as one trigger for it to be activated when `messages` is non-empty and `sender` is `None`.
        Use registered auto reply functions to generate replies.
        By default, the following functions are checked in order:
        1. check_termination_and_human_reply
        2. generate_function_call_reply (deprecated in favor of tool_calls)
        3. generate_tool_calls_reply
        4. generate_code_execution_reply
        5. generate_oai_reply
        Every function returns a tuple (final, reply).
        When a function returns final=False, the next function will be checked.
        So by default, termination and human reply will be checked first.
        If not terminating and human reply is skipped, execute function or code and return the result.
        AI replies are generated only when no code execution is performed.

        Args:
            messages: a list of messages in the conversation history.
            sender: sender of an Agent instance.

        Additional keyword arguments:
            exclude (List[Callable]): a list of reply functions to be excluded.

        Returns:
            str or dict or None: reply. None if no reply is generated.
        """
        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        # Call the hookable method that gives registered hooks a chance to process the last message.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_last_received_message(messages)

        # Call the hookable method that gives registered hooks a chance to process all messages.
        # Message modifications do not affect the incoming messages or self._oai_messages.
        messages = self.process_all_messages_before_reply(messages)

        for reply_func_tuple in self._reply_func_list:
            reply_func = reply_func_tuple["reply_func"]
            if "exclude" in kwargs and reply_func in kwargs["exclude"]:
                continue
            if inspect.iscoroutinefunction(reply_func):
                continue
            if self._match_trigger(reply_func_tuple["trigger"], sender):
                final, reply = reply_func(
                    self, messages=messages, sender=sender, config=reply_func_tuple["config"])
                if logging_enabled():
                    log_event(
                        self,
                        "reply_func_executed",
                        reply_func_module=reply_func.__module__,
                        reply_func_name=reply_func.__name__,
                        final=final,
                        reply=reply,
                    )
                if final:
                    if reply is None:
                        self.SpeakText("Thank you signing off")
                        return reply
                    self.SpeakText(command=reply)
                    return reply
        self.SpeakText(command=self._default_auto_reply)
        return self._default_auto_reply

user_proxy = ListeningUser(
    name="User",
    human_input_mode="ALWAYS",
    code_execution_config=False,
    description="A user agent that takes voice input from user"
)

assistant = SpeakingAssistant(
    name="Assistant",
    system_message="You are a handy assistant that only replies to query from your knowledge. You do not write any code",
    llm_config=llm_config,
    description="An assistant agent that can help answer common queries",
    is_termination_msg=lambda x : x.get("content","").find("terminate") >= 0
)


def main(start_command: Annotated[str, "The starter message"]) -> None:
    user_proxy.initiate_chat(assistant, message=start_command)