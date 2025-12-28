"""Data models for board verification."""

from typing import List, Optional, Literal, NamedTuple
from pydantic import BaseModel, Field


class WordEntry(BaseModel):
    """Represents a word placement on the board."""
    word: str = Field(..., min_length=1, pattern=r'^[A-Z]+$')
    direction: Literal['H', 'V']
    target: Optional[str] = None
    target_idx: Optional[int] = Field(None, ge=0)
    word_idx: Optional[int] = Field(None, ge=0)


class Position(NamedTuple):
    """Represents a word's position on the grid."""
    x: int
    y: int
    direction: str


class ValidationError(BaseModel):
    """A single validation error."""
    code: str
    message: str
    word: Optional[str] = None
    line: Optional[int] = None
    cascade_level: int = 0  # 0=FATAL, 1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW


class ValidationResult(BaseModel):
    """Result of board validation."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    words: List[str] = Field(default_factory=list)
    grid: Optional[str] = None
    tiles_used: int = 0
    letters_used: List[str] = Field(default_factory=list)  # Actual letters on grid

