from autogen.agentchat import ConversableAgent,register_function,GroupChat,GroupChatManager,UserProxyAgent
from autogen.agentchat.contrib.society_of_mind_agent import SocietyOfMindAgent
from autogen.agentchat.conversable_agent import logger,IOStream
from autogen import Agent
from autogen.runtime_logging import logging_enabled, log_event
from dotenv import load_dotenv
from typing_extensions import Annotated,Optional,List,Dict,Union
from typing import Any
import inspect
import os

#Tool imports
from tools import recognize_speech,speak_text,use_llm
from agent_tools import insert_item_to_db,view_item,update_cost_price,update_selling_price,update_units


env_path = "D:/ABRAR/1_PERSONAL/Wolf_Tech/Mazduur_AI/app/.env"
load_dotenv(env_path)


config_list = [{"model": "llama3-70b-8192",
                "api_key": os.environ["GROQ_KEY"],
                "base_url": "https://api.groq.com/openai/v1",
                "max_retries": 10}]

llm_config = {"config_list":config_list,"temperature":0.75,"cache_seed":None}


class ListeningUser(ConversableAgent):
    def get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        
        iostream = IOStream.get_default()

        choice = iostream.input("Choose your input type\n1.Type\n2.Speak\n")
        if choice == '1':
            reply = iostream.input("Enter your command\n")
        else:
            reply = recognize_speech()
        self._human_input.append(reply)
        return reply


class SpeakingAssistant(ConversableAgent):

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
                        speak_text("Thank you signing off")
                        return reply
                    elif 'tool_call' in reply:
                        return reply
                    speak_text(command=reply)
                    return reply
        speak_text(command=self._default_auto_reply)
        return self._default_auto_reply

tool_suggestor = ConversableAgent(
    name="Tool-Suggestor",
    system_message="""
    You are a Tool Suggestor for an E Commerce Company
    Your role is to suggest tools that should be executed to complete a task
    The context of all tasks and questions are about the products of the company
    """,
    human_input_mode="NEVER",
    llm_config=llm_config,
    description="An agent to suggest a tool for a particular task"
)

tool_executor = ConversableAgent(
    name="Tool-Executor",
    system_message="You are a tool executor, your job is to execute the tools suggested to you by the assistant",
    human_input_mode="NEVER",
    llm_config=llm_config,
    description="An agent for executing a tool suggested by the agent"
)

#Registering assistant tools
register_function(
    f=insert_item_to_db,
    caller=tool_suggestor,
    executor=tool_executor,
    name="Insert-Product",
    description="A tool to insert a product into the database"
)

register_function(
    f=update_units,
    caller=tool_suggestor,
    executor=tool_executor,
    name="Update-Product-Units",
    description="A tool to update the number of units of a product in the database"
)

register_function(
    f=update_cost_price,
    caller=tool_suggestor,
    executor=tool_executor,
    name="Update-Product-Cost-Price",
    description="A tool to update the cost price of a product in the database"
)

register_function(
    f=update_selling_price,
    caller=tool_suggestor,
    executor=tool_executor,
    name="Update-Product-Selling-Price",
    description="A tool to update the selling price of a product in the database"
)


register_function(
    f=view_item,
    caller=tool_suggestor,
    executor=tool_executor,
    name="View-Product",
    description="A tool to view all the details of a product"
)


user_proxy = ListeningUser(
    name="User",
    human_input_mode="ALWAYS",
    code_execution_config=False,
    description="A user agent that takes voice input from user"
)

assistant = SpeakingAssistant(
    name="Assistant",
    system_message="""You are a handy assistant that only replies to query from your knowledge. You do not write any code
    You will receieve a message from the Commander-Agent, from that extract the answer that the user requires
    Call the Commander-Agent when a task needs to be done by the user""",
    llm_config=llm_config,
    description="An assistant agent that can help answer queries",
    is_termination_msg=lambda x: x.get("content", "").find("terminate") >= 0
)

# setting up main conversation loop
main_groupchat = GroupChat(
    agents=[user_proxy, tool_suggestor, tool_executor],
    messages=[],
    admin_name="User",
    speaker_selection_method="round_robin",
    send_introductions=True,
    select_speaker_auto_verbose=True,
    allow_repeat_speaker=False,
    role_for_select_speaker_messages="user"
)

main_chat_manager = GroupChatManager(
    groupchat=main_groupchat,
    name="Main-Manager",
    human_input_mode="NEVER",
    system_message="""
    You have three agents to manage
    Assistant - An assistant agent that can help answer queries
    Commander-Agent - An agent to acheive a given task
    User - The agent to confirm if the task is completed or a next step is required
    """,
    is_termination_msg=lambda x: (x.get("content", "").find("terminate") >= 0) or (x.get("content", "").find("done") >= 0),
    llm_config=False,
)

def main(start_command: Annotated[str, "The starter message"]) -> None:
    user_proxy.initiate_chat(main_chat_manager, message=start_command)
