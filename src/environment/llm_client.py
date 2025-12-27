from typing import List, Dict, Any, Optional
import litellm

from .models import Message, Role


class LLMClient:
    """
    Client for managing LLM interactions via LiteLLM.

    Maintains conversation history and handles API calls to various LLM providers.
    """

    def __init__(
        self,
        model: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ):
        """
        Initialize the LLM client.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-opus-20240229")
            temperature: Sampling temperature (default: 1.0)
            max_tokens: Maximum tokens to generate (default: None, uses model default)
            **kwargs: Additional arguments to pass to litellm.completion()
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.additional_params = kwargs
        self.messages: List[Dict[str, str]] = []

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

    def completion(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Any:
        """
        Generate a completion using the current message history.

        Args:
            temperature: Override the default temperature
            max_tokens: Override the default max_tokens
            **kwargs: Additional arguments to pass to litellm.completion()

        Returns:
            The completion response from LiteLLM
        """
        params = {
            "model": self.model,
            "messages": self.messages,
            "temperature": temperature if temperature is not None else self.temperature,
            **self.additional_params,
            **kwargs
        }

        if max_tokens is not None or self.max_tokens is not None:
            params["max_tokens"] = max_tokens if max_tokens is not None else self.max_tokens

        response = litellm.completion(**params)
        return response
