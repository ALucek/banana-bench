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

    def completion(self, **kwargs: Any) -> Any:
        """
        Generate a completion using the current message history.

        Args:
            **kwargs: Additional arguments to pass to litellm.completion()

        Returns:
            The completion response from LiteLLM
        """
        params = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            **self.additional_params,
            **kwargs
        }

        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        return litellm.completion(**params)
