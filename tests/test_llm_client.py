from unittest.mock import Mock, patch
import pytest

from src.environment import LLMClient, Message, Role


def create_mock_response(content: str = "Test response", model: str = "gpt-5-nano") -> Mock:
    """
    Create a realistic mock response matching litellm's ModelResponse structure.

    Based on actual response:
    ModelResponse(
        id='chatcmpl-...',
        created=1766865888,
        model='gpt-5-mini-2025-08-07',
        object='chat.completion',
        choices=[Choices(
            finish_reason='stop',
            index=0,
            message=Message(content='...', role='assistant', ...)
        )],
        usage=Usage(completion_tokens=18, prompt_tokens=8, total_tokens=26, ...)
    )
    """
    return Mock(
        id='chatcmpl-test123',
        created=1766865888,
        model=model,
        object='chat.completion',
        system_fingerprint=None,
        choices=[
            Mock(
                finish_reason='stop',
                index=0,
                message=Mock(
                    content=content,
                    role='assistant',
                    tool_calls=None,
                    function_call=None
                )
            )
        ],
        usage=Mock(
            completion_tokens=10,
            prompt_tokens=5,
            total_tokens=15
        ),
        service_tier='default'
    )


class TestLLMClientInitialization:
    """Test cases for LLM client initialization."""

    def test_init_with_model_only(self):
        """Initialize with just a model name."""
        client = LLMClient(model="gpt-5-nano")
        assert client.model == "gpt-5-nano"
        assert client.temperature == 1.0
        assert client.max_tokens is None
        assert client.messages == []

    def test_init_with_temperature(self):
        """Initialize with custom temperature."""
        client = LLMClient(model="gpt-5-nano", temperature=0.5)
        assert client.temperature == 0.5

    def test_init_with_max_tokens(self):
        """Initialize with max_tokens."""
        client = LLMClient(model="gpt-5-nano", max_tokens=100)
        assert client.max_tokens == 100

    def test_init_with_additional_params(self):
        """Initialize with additional litellm parameters."""
        client = LLMClient(model="gpt-5-nano", top_p=0.9, frequency_penalty=0.5)
        assert client.additional_params["top_p"] == 0.9
        assert client.additional_params["frequency_penalty"] == 0.5


class TestMessageManagement:
    """Test cases for message management."""

    def test_add_single_message(self):
        """Add a single message to conversation."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Hello!")

        assert len(client.messages) == 1
        assert client.messages[0]["role"] == "user"
        assert client.messages[0]["content"] == "Hello!"

    def test_add_multiple_messages(self):
        """Add multiple messages in sequence."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("system", "You are a helpful assistant.")
        client.add_message("user", "What is 2+2?")
        client.add_message("assistant", "4")

        assert len(client.messages) == 3
        assert client.messages[0]["role"] == "system"
        assert client.messages[1]["role"] == "user"
        assert client.messages[2]["role"] == "assistant"

    def test_add_message_with_all_roles(self):
        """Test adding messages with all valid roles."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("system", "System message")
        client.add_message("user", "User message")
        client.add_message("assistant", "Assistant message")

        assert len(client.messages) == 3
        roles = [msg["role"] for msg in client.messages]
        assert roles == ["system", "user", "assistant"]

    def test_clear_messages(self):
        """Clear all messages from conversation."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Message 1")
        client.add_message("user", "Message 2")
        assert len(client.messages) == 2

        client.clear_messages()
        assert len(client.messages) == 0

    def test_get_messages_returns_copy(self):
        """get_messages should return a copy, not reference."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Hello!")

        messages = client.get_messages()
        messages.append({"role": "user", "content": "Should not affect client"})

        assert len(client.messages) == 1
        assert len(messages) == 2

    def test_get_messages_format(self):
        """Messages should be in OpenAI chat format."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Test message")

        messages = client.get_messages()
        assert isinstance(messages, list)
        assert isinstance(messages[0], dict)
        assert "role" in messages[0]
        assert "content" in messages[0]


class TestCompletion:
    """Test cases for completion generation."""

    @patch('litellm.completion')
    def test_completion_basic(self, mock_completion):
        """Test basic completion call."""
        mock_completion.return_value = create_mock_response(content="Hello!")

        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Hi")
        response = client.completion()

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "gpt-5-nano"
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]
        assert call_kwargs["temperature"] == 1.0

        # Verify response structure
        assert response.choices[0].message.content == "Hello!"
        assert response.choices[0].message.role == "assistant"

    @patch('litellm.completion')
    def test_completion_with_default_max_tokens(self, mock_completion):
        """Test completion uses default max_tokens when set."""
        mock_completion.return_value = create_mock_response()

        client = LLMClient(model="gpt-5-nano", max_tokens=150)
        client.add_message("user", "Test")
        client.completion()

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 150

    @patch('litellm.completion')
    def test_completion_without_max_tokens(self, mock_completion):
        """Test completion without max_tokens set."""
        mock_completion.return_value = create_mock_response()

        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Test")
        client.completion()

        call_kwargs = mock_completion.call_args[1]
        assert "max_tokens" not in call_kwargs

    @patch('litellm.completion')
    def test_completion_with_additional_params(self, mock_completion):
        """Test completion includes additional parameters."""
        mock_completion.return_value = create_mock_response()

        client = LLMClient(model="gpt-5-nano", top_p=0.9, frequency_penalty=0.5)
        client.add_message("user", "Test")
        client.completion()

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["frequency_penalty"] == 0.5

    @patch('litellm.completion')
    def test_completion_with_kwargs_override(self, mock_completion):
        """Test completion with additional kwargs in call."""
        mock_completion.return_value = create_mock_response()

        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Test")
        client.completion(stream=True, n=2)

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["stream"] is True
        assert call_kwargs["n"] == 2

    @patch('litellm.completion')
    def test_completion_returns_response(self, mock_completion):
        """Test completion returns the litellm response."""
        expected_response = create_mock_response(content="Custom response")
        mock_completion.return_value = expected_response

        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Test")
        response = client.completion()

        assert response == expected_response
        assert response.choices[0].message.content == "Custom response"
        assert response.model == "gpt-5-nano"
        assert response.usage.total_tokens == 15


class TestMessageModel:
    """Test cases for Message model validation."""

    def test_valid_message_user(self):
        """Create valid user message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_valid_message_assistant(self):
        """Create valid assistant message."""
        msg = Message(role="assistant", content="Hi there")
        assert msg.role == "assistant"

    def test_valid_message_system(self):
        """Create valid system message."""
        msg = Message(role="system", content="You are helpful")
        assert msg.role == "system"

    def test_message_model_dump(self):
        """Message should serialize to dict."""
        msg = Message(role="user", content="Test")
        dumped = msg.model_dump()
        assert dumped == {"role": "user", "content": "Test"}

    def test_invalid_role(self):
        """Invalid role should raise validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            Message(role="invalid", content="Test")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_content(self):
        """Messages with empty content should be allowed."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "")
        assert len(client.messages) == 1
        assert client.messages[0]["content"] == ""

    def test_long_content(self):
        """Messages with very long content should work."""
        client = LLMClient(model="gpt-5-nano")
        long_content = "A" * 10000
        client.add_message("user", long_content)
        assert client.messages[0]["content"] == long_content

    def test_multiple_clears(self):
        """Multiple clears should work without error."""
        client = LLMClient(model="gpt-5-nano")
        client.add_message("user", "Test")
        client.clear_messages()
        client.clear_messages()
        assert len(client.messages) == 0


    @patch('litellm.completion')
    def test_completion_with_empty_messages(self, mock_completion):
        """Completion with no messages should still call API."""
        mock_completion.return_value = create_mock_response()

        client = LLMClient(model="gpt-5-nano")
        client.completion()

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["messages"] == []

    def test_temperature_zero(self):
        """Temperature of 0 should be valid."""
        client = LLMClient(model="gpt-5-nano", temperature=0.0)
        assert client.temperature == 0.0

    def test_temperature_one(self):
        """Temperature of 1 should be valid."""
        client = LLMClient(model="gpt-5-nano", temperature=1.0)
        assert client.temperature == 1.0

    def test_temperature_above_one(self):
        """Temperature above 1 should be allowed (some providers support this)."""
        client = LLMClient(model="gpt-5-nano", temperature=2.0)
        assert client.temperature == 2.0
