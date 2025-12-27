from typing import Literal
from pydantic import BaseModel


Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Role
    content: str
