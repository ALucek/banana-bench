from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field
import litellm

from .models import Message, Role


class LLMClient(BaseModel):
    """
    Client for managing LLM interactions via LiteLLM.

    Maintains conversation history and handles API calls to various LLM providers.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

    model: str
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    messages: List[Dict[str, str]] = Field(default_factory=list)

    @property
    def additional_params(self) -> Dict[str, Any]:
        """Get additional parameters passed during initialization."""
        # Pydantic stores extra fields in __pydantic_extra__
        return self.__pydantic_extra__ if hasattr(self, '__pydantic_extra__') and self.__pydantic_extra__ else {}

    def add_message(self, role: Role, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: The role of the message sender ("system", "user", or "assistant")
            content: The message content
        """
        message = Message(role=role, content=content)
        self.messages.append(message.model_dump())

    def clear_messages(self) -> None:
        """Clear all messages from the conversation history."""
        self.messages = []

    def get_messages(self) -> List[Dict[str, str]]:
        """
        Get the current conversation history.

        Returns:
            List of message dictionaries in OpenAI format
        """
        return self.messages.copy()

    def _get_trimmed_messages(self, max_pairs: int = 10) -> List[Dict[str, str]]:
        """
        Get trimmed message history keeping system prompt + last N user/assistant pairs.

        Args:
            max_pairs: Maximum number of user/assistant message pairs to keep (default 10)

        Returns:
            Trimmed list of messages (system + last N pairs = max 21 messages)
        """
        if not self.messages:
            return []

        # Separate system message from conversation
        system_msg = None
        conversation = []

        for msg in self.messages:
            if msg["role"] == "system":
                system_msg = msg
            else:
                conversation.append(msg)

        # Keep only the last (max_pairs * 2) messages from conversation
        # This keeps the last max_pairs user/assistant pairs
        max_conversation_msgs = max_pairs * 2
        trimmed_conversation = conversation[-max_conversation_msgs:] if len(conversation) > max_conversation_msgs else conversation

        # Reconstruct: system + trimmed conversation
        result = []
        if system_msg:
            result.append(system_msg)
        result.extend(trimmed_conversation)

        return result

    def completion(self, **kwargs: Any) -> Any:
        """
        Generate a completion using trimmed message history (system + last 10 pairs).

        Args:
            **kwargs: Additional arguments to pass to litellm.completion()

        Returns:
            The completion response from LiteLLM
        """
        # Use trimmed messages for efficiency (system + last 10 user/assistant pairs)
        # This provides ~50 messages of context for long games
        trimmed_messages = self._get_trimmed_messages(max_pairs=10)

        params = {
            "model": self.model,
            "messages": trimmed_messages,
            "temperature": self.temperature,
            **self.additional_params,
            **kwargs
        }

        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        # If reasoning_effort is specified (OpenAI compatibility), allow it through
        if "reasoning_effort" in params:
            params.setdefault("allowed_openai_params", [])
            if "reasoning_effort" not in params["allowed_openai_params"]:
                params["allowed_openai_params"].append("reasoning_effort")

        return litellm.completion(**params)
