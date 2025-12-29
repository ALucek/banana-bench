"""
Pydantic models for the environment layer.

This module contains all the data models (configurations, results, parsed responses)
used throughout the environment layer. The main logic classes (Game, Player, LLMClient,
BananaBench) remain in their respective files.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

from ..verifiers.models import ValidationResult


# Type aliases
Role = Literal["system", "user", "assistant"]
Action = Literal["DUMP", "NONE"]


class Message(BaseModel):
    """Represents a single message in the conversation."""
    role: Role
    content: str


class ParsedResponse(BaseModel):
    """Parsed components from an LLM response."""
    thinking: Optional[str] = None
    action: Action = "NONE"
    dump_tile: Optional[str] = None  # The tile to dump, if action is DUMP
    board: Optional[str] = None  # Raw board XML content
    raw_response: str = ""


class TurnResult(BaseModel):
    """Result of a single player turn."""
    player_id: str
    turn_number: int
    action: Action
    dump_tile: Optional[str] = None
    board_spec: Optional[str] = None
    validation: Optional[ValidationResult] = None
    thinking: Optional[str] = None
    tiles_before: List[str] = Field(default_factory=list)
    tiles_after: List[str] = Field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None
    auto_peeled: bool = False
    auto_bananas: bool = False
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class PlayerConfig(BaseModel):
    """Configuration for a single player."""
    model_config = ConfigDict(extra='allow')

    model: str
    name: Optional[str] = None
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    # Additional kwargs are allowed and passed to LiteLLM


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark run."""
    max_turns: int = 100
    seed: Optional[int] = None
    players: List[PlayerConfig] = Field(default_factory=lambda: [PlayerConfig(model="gpt-4o")])

    @property
    def num_players(self) -> int:
        """Number of players (automatically derived from players list)."""
        return len(self.players)


class BenchmarkResult(BaseModel):
    """Result of a complete benchmark run."""
    config: BenchmarkConfig
    winner: Optional[str] = None
    total_turns: int = 0
    end_reason: str = ""
    player_results: Dict[str, Dict] = Field(default_factory=dict)
    turn_history: List[TurnResult] = Field(default_factory=list)
    game_state: Dict = Field(default_factory=dict)
    conversation_history: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
