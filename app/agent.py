"""
LangGraph Agent with Production Error Handling
Retry logic, model fallback, and structured state management.
"""

from typing import Optional
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langsmith import traceable

from app.config import get_settings


# === Agent State ===

'''
Using a TypedDict for state allows us to define the structure of our agent's state clearly.
The Annotated type with add_messages reducer allows us to accumulate messages in a list as the agent 
processes input and generates output.

This structured state management is crucial for maintaining context across retries and model fallbacks, 
ensuring that the agent can provide coherent responses even in the face of errors or timeouts.

The AgentState includes:
- messages: A list of BaseMessage objects that represent the conversation history. The add_messages reducer
  allows us to easily append new messages to this list as the agent processes input and generates output.
- error: An optional string that holds any error message encountered during processing. This allows the agent
  to track errors and make decisions based on whether an error occurred.
- retry_count: An integer that tracks how many times the agent has attempted to process the message
  with the primary model. This is used to determine when to switch to the fallback model.
- model_used: A string that indicates which model was used to generate the response (e.g
  "primary", "fallback", or "error_handler"). This can be useful for monitoring and debugging purposes.
'''

class AgentState(TypedDict):
    """
    State for the production agent.
    Uses Annotated with add_messages reducer for message accumulation.
    """
    messages: Annotated[list[BaseMessage], add_messages]    # Accumulate messages in a list
    error: Optional[str]    # Store error message if any
    retry_count: int        # Number of retry attempts
    model_used: str         # Model used for the response
    
# === Agent Builder ===

class ProductionAgent:
    """
    Production LangGraph agent with:
    - Retry on failure (model fallback)
    - Graceful error handling
    - LangSmith tracing
    """

    '''
    The ProductionAgent class implements a robust LangGraph agent designed for production use. 
    It features retry logic with model fallback, graceful error handling, and structured state 
    management using a TypedDict.
    Key features:
        - Retry Logic: The agent attempts to process the message with a primary model. If it 
          encounters an error, it retries with a fallback model up to a specified number of retries. 
          This increases the likelihood of successfully processing the message even if the primary 
          model experiences issues.
        - Graceful Error Handling: If both the primary and fallback models fail, the agent returns 
          a user-friendly error message instead of exposing raw error details. This ensures a better 
          user experience while still providing useful information for monitoring and debugging.
        - Structured State Management: The agent's state is defined using a TypedDict, which includes 
          fields for messages, error tracking, retry count, and model usage. This structured approach 
          allows for clear and maintainable state management throughout the agent's processing flow.
        - LangSmith Tracing: The invoke method is decorated with @traceable, allowing for detailed 
          tracing of the agent's execution in LangSmith. This provides valuable insights into the 
          agent's behavior and performance in production, aiding in monitoring and debugging efforts.
    '''

    def __init__(self):
        settings = get_settings()

        self.primary_llm = ChatOpenAI(
            model=settings.primary_model,
            temperature=0,
            timeout=30,     # Set a reasonable timeout for production to avoid hanging requests
            max_retries=0,  # We handle retries ourselves
            api_key=settings.openai_api_key,    # Ensure API key is set in production environment variables
        )
        self.fallback_llm = ChatOpenAI(
            model=settings.fallback_model,
            temperature=0,
            timeout=30,
            max_retries=0,
            api_key=settings.openai_api_key,
        )
        self.max_retries = settings.max_retries
        self.graph = self._build_graph()    # Build the LangGraph state machine

    def _build_graph(self):
        """Build the LangGraph state machine."""

        # Define the functions for each node in the graph. These functions will be called with 
        # the current state and should return a new state.
        def process_message(state: AgentState) -> dict:
            """Try to process the message with the primary model."""
            try:
                response = self.primary_llm.invoke(state["messages"])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": "primary",
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "retry_count": state["retry_count"] + 1,
                    "model_used": "",
                }

        def try_fallback(state: AgentState) -> dict:
            """Fallback to secondary model."""
            try:
                response = self.fallback_llm.invoke(state["messages"])
                return {
                    "messages": [response],
                    "error": None,
                    "model_used": "fallback",
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "model_used": "",
                }

        def handle_error(state: AgentState) -> dict:
            """Return a graceful error message."""
            return {
                "messages": [
                    AIMessage(content=(
                        "I'm sorry, I'm having trouble processing your request "
                        "right now. Please try again in a moment."
                    ))
                ],
                "model_used": "error_handler",
            }

        def route_after_process(state: AgentState) -> str:
            """Decide what to do after primary model attempt."""

            # This routing function checks the state after attempting to process the message 
            # with the primary model. If there was no error, it routes to "done". If there 
            # was an error and we have retries left, it routes to "fallback". Otherwise, 
            # it routes to "error".
            if state.get("error") is None:
                return "done"
            elif state["retry_count"] < self.max_retries:
                return "fallback"
            else:
                return "error"

        def route_after_fallback(state: AgentState) -> str:
            """Decide what to do after fallback attempt."""
            if state.get("error") is None:
                return "done"
            else:
                return "error"

        # Build the graph
        graph = StateGraph(AgentState)

        graph.add_node("process", process_message)
        graph.add_node("fallback", try_fallback)
        graph.add_node("error", handle_error)

        graph.add_edge(START, "process")
        graph.add_conditional_edges(
            "process",
            route_after_process,
            {"done": END, "fallback": "fallback", "error": "error"},
        )
        graph.add_conditional_edges(
            "fallback",
            route_after_fallback,
            {"done": END, "error": "error"},
        )
        graph.add_edge("error", END)

        return graph.compile()

    @traceable(name="production_agent_invoke")
    def invoke(self, message: str) -> dict:
        """
        Invoke the agent with a user message.
        Returns: {"response": str, "model_used": str, "error": str | None}
        """
        result = self.graph.invoke({
            "messages": [HumanMessage(content=message)],
            "error": None,
            "retry_count": 0,
            "model_used": "",
        })

        return {
            "response": result["messages"][-1].content,
            "model_used": result.get("model_used", "unknown"),
            "error": result.get("error"),
        }
    
# uv run python -c "
# from app.agent import ProductionAgent
# agent = ProductionAgent()
# resp = agent.invoke('What is LangGraph in one sentence?')
# print(resp)
# "