"""
Player class for managing individual player state and LLM interaction.

Handles player hand, board state, and coordinates with the LLM client
to generate moves.
"""

import re
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict

from .llm_client import LLMClient
from ..verifiers.verify import verify
from ..verifiers.models import ValidationResult


Action = Literal["DUMP", "NONE"]


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


class Player(BaseModel):
    """
    Manages individual player state and LLM interaction.
    
    Handles the player's hand, current board, and coordinates
    prompting and response parsing for the LLM.
    
    Attributes:
        player_id: Unique identifier for the player
        name: Display name for the player
        hand: Current tiles in the player's hand
        board_spec: Current board specification (XML format)
        llm_client: LLM client for generating moves
        turn_count: Number of turns taken
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    player_id: str
    name: str = ""
    hand: List[str] = Field(default_factory=list)
    board_spec: Optional[str] = None
    llm_client: Optional[LLMClient] = None
    turn_count: int = 0
    last_validation: Optional[ValidationResult] = None
    
    def model_post_init(self, __context) -> None:
        """Set default name if not provided."""
        if not self.name:
            self.name = f"Player {self.player_id}"
    
    @classmethod
    def create(
        cls,
        player_id: str,
        model: str,
        name: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **llm_kwargs: Any
    ) -> "Player":
        """
        Factory method to create a player with an LLM client.
        
        Args:
            player_id: Unique identifier for the player
            model: LLM model name (e.g., "gpt-4o", "claude-3-opus")
            name: Optional display name
            temperature: LLM temperature setting
            max_tokens: Optional max tokens for responses
            **llm_kwargs: Additional arguments for the LLM client
            
        Returns:
            A new Player instance with configured LLM client
        """
        llm_client = LLMClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **llm_kwargs
        )
        
        return cls(
            player_id=player_id,
            name=name or f"Player {player_id}",
            llm_client=llm_client
        )
    
    @property
    def tiles_in_hand(self) -> int:
        """Number of tiles currently in hand."""
        return len(self.hand)
    
    @property
    def hand_summary(self) -> Dict[str, int]:
        """Get a count of each letter in hand."""
        summary: Dict[str, int] = {}
        for tile in self.hand:
            summary[tile] = summary.get(tile, 0) + 1
        return dict(sorted(summary.items()))
    
    def add_tiles(self, tiles: List[str]) -> None:
        """
        Add tiles to the player's hand.
        
        Args:
            tiles: List of tiles to add
        """
        self.hand.extend([t.upper() for t in tiles])
    
    def remove_tile(self, tile: str) -> bool:
        """
        Remove a tile from the player's hand.
        
        Args:
            tile: The tile to remove
            
        Returns:
            True if tile was removed, False if not found
        """
        tile = tile.upper()
        if tile in self.hand:
            self.hand.remove(tile)
            return True
        return False
    
    def has_tile(self, tile: str) -> bool:
        """Check if player has a specific tile."""
        return tile.upper() in self.hand
    
    def set_starting_hand(self, tiles: List[str]) -> None:
        """
        Set the player's starting hand.
        
        Args:
            tiles: List of tiles for the starting hand
        """
        self.hand = [t.upper() for t in tiles]
        self.board_spec = None
        self.turn_count = 0
        self.last_validation = None
    
    @staticmethod
    def parse_response(response: str) -> ParsedResponse:
        """
        Parse an LLM response for thinking, action, and board content.
        
        Expected format:
        <think>reasoning here</think>
        <action>PEEL|DUMP X|BANANAS</action>
        <board>board spec here</board>
        
        Args:
            response: Raw LLM response text
            
        Returns:
            ParsedResponse with extracted components
        """
        result = ParsedResponse(raw_response=response)
        
        # Extract thinking/game_plan
        think_match = re.search(r'<game_plan>(.*?)</game_plan>', response, re.DOTALL)
        if think_match:
            result.thinking = think_match.group(1).strip()
        
        # Extract action
        action_match = re.search(r'<action>(.*?)</action>', response, re.DOTALL)
        if action_match:
            action_content = action_match.group(1).strip().upper()
            
            if action_content.startswith("DUMP"):
                result.action = "DUMP"
                # Extract the tile to dump (e.g., "DUMP Q" -> "Q")
                dump_match = re.match(r'DUMP\s+([A-Z])', action_content)
                if dump_match:
                    result.dump_tile = dump_match.group(1)
            else:
                result.action = "NONE"
        
        # Extract board
        board_match = re.search(r'<board>(.*?)</board>', response, re.DOTALL)
        if board_match:
            result.board = board_match.group(1).strip()
        
        return result
    
    def validate_board(self, board_spec: str) -> ValidationResult:
        """
        Validate a board specification.
        
        Args:
            board_spec: The board specification to validate
            
        Returns:
            ValidationResult from the verifier
        """
        return verify(board_spec)
    
    def get_state(self) -> Dict:
        """
        Get the current player state as a dictionary.
        
        Useful for serialization and logging.
        
        Returns:
            Dictionary containing player state
        """
        return {
            "player_id": self.player_id,
            "name": self.name,
            "tiles_in_hand": self.tiles_in_hand,
            "hand": sorted(self.hand),
            "hand_summary": self.hand_summary,
            "turn_count": self.turn_count,
            "has_board": self.board_spec is not None,
            "last_validation_valid": self.last_validation.valid if self.last_validation else None,
        }
