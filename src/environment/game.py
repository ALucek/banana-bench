import random
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


# Standard Bananagrams tile distribution (144 tiles total)
TILE_DISTRIBUTION: Dict[str, int] = {
    "A": 13, "B": 3, "C": 3, "D": 6, "E": 18, "F": 3, "G": 4,
    "H": 3, "I": 12, "J": 2, "K": 2, "L": 5, "M": 3, "N": 8,
    "O": 11, "P": 3, "Q": 2, "R": 9, "S": 6, "T": 9, "U": 6,
    "V": 3, "W": 3, "X": 2, "Y": 3, "Z": 2
}

# Starting hand sizes based on player count
STARTING_TILES: Dict[int, int] = {
    1: 21,  # Solitaire
    2: 21,
    3: 21,
    4: 21,
    5: 15,
    6: 15,
    7: 11,
    8: 11,
}


class Game(BaseModel):
    """
    Manages the central Bananagrams game state.
    
    Handles the tile pool (bunch), tile distribution, and game rules
    for DUMP and PEEL operations.
    
    Attributes:
        bunch: The remaining tiles in the central pool
        num_players: Number of players in the game
        is_end_state: Whether the game has reached the end condition
        seed: Optional random seed for reproducibility
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    bunch: List[str] = Field(default_factory=list)
    num_players: int = Field(default=1, ge=1, le=8)
    is_end_state: bool = Field(default=False)
    seed: Optional[int] = None
    _rng: random.Random = None
    
    def model_post_init(self, __context) -> None:
        """Initialize the random generator after model creation."""
        self._rng = random.Random(self.seed)
    
    @classmethod
    def create(cls, num_players: int = 1, seed: Optional[int] = None) -> "Game":
        """
        Factory method to create a new game with a shuffled tile pool.
        
        Args:
            num_players: Number of players (1-8)
            seed: Optional random seed for reproducibility
            
        Returns:
            A new Game instance with shuffled tiles
        """
        # Create the full tile pool from distribution
        bunch = []
        for letter, count in TILE_DISTRIBUTION.items():
            bunch.extend([letter] * count)
        
        # Shuffle the tiles
        rng = random.Random(seed)
        rng.shuffle(bunch)
        
        return cls(bunch=bunch, num_players=num_players, seed=seed)
    
    @property
    def tiles_remaining(self) -> int:
        """Number of tiles remaining in the bunch."""
        return len(self.bunch)
    
    @property
    def starting_hand_size(self) -> int:
        """Get the starting hand size for this game's player count."""
        return STARTING_TILES.get(self.num_players, 21)
    
    def draw_starting_hand(self) -> List[str]:
        """
        Draw a starting hand for a player.
        
        Returns:
            List of tiles for the player's starting hand
            
        Raises:
            ValueError: If not enough tiles in the bunch
        """
        hand_size = self.starting_hand_size
        if len(self.bunch) < hand_size:
            raise ValueError(
                f"Not enough tiles in bunch ({len(self.bunch)}) "
                f"to draw starting hand ({hand_size})"
            )
        
        hand = self.bunch[:hand_size]
        self.bunch = self.bunch[hand_size:]
        self._check_end_state()
        return hand
    
    def peel(self) -> List[str]:
        """
        Execute a PEEL: draw one tile for each player.
        
        When a player uses all their tiles, they call PEEL and
        everyone (including them) draws one tile from the bunch.
        
        Returns:
            List of tiles (one per player)
            
        Raises:
            ValueError: If not enough tiles for all players
        """
        if len(self.bunch) < self.num_players:
            raise ValueError(
                f"Not enough tiles in bunch ({len(self.bunch)}) "
                f"for PEEL ({self.num_players} players)"
            )
        
        tiles = self.bunch[:self.num_players]
        self.bunch = self.bunch[self.num_players:]
        self._check_end_state()
        return tiles
    
    def dump(self, tile: str) -> List[str]:
        """
        Execute a DUMP: return one tile, receive three.
        
        A player can dump a difficult tile back into the bunch
        but must take three tiles in return.
        
        Args:
            tile: The tile to return to the bunch
            
        Returns:
            List of 3 new tiles
            
        Raises:
            ValueError: If not enough tiles in bunch for the exchange
        """
        if len(self.bunch) < 3:
            raise ValueError(
                f"Not enough tiles in bunch ({len(self.bunch)}) for DUMP (need 3)"
            )
        
        # Draw 3 tiles first
        new_tiles = self.bunch[:3]
        self.bunch = self.bunch[3:]
        
        # Return the dumped tile to a random position in the bunch
        if self.bunch:
            insert_pos = self._rng.randint(0, len(self.bunch))
            self.bunch.insert(insert_pos, tile.upper())
        else:
            self.bunch = [tile.upper()]
        
        self._check_end_state()
        return new_tiles
    
    def _check_end_state(self) -> None:
        """Update the end state flag based on remaining tiles."""
        # End state: bunch has fewer tiles than number of players
        # This means no more PEELs are possible
        self.is_end_state = len(self.bunch) < self.num_players
    
    def can_peel(self) -> bool:
        """Check if a PEEL operation is possible."""
        return len(self.bunch) >= self.num_players
    
    def can_dump(self) -> bool:
        """Check if a DUMP operation is possible."""
        return len(self.bunch) >= 3
    
    def get_state(self) -> Dict:
        """
        Get the current game state as a dictionary.
        
        Useful for serialization and logging.
        
        Returns:
            Dictionary containing game state
        """
        return {
            "tiles_remaining": self.tiles_remaining,
            "num_players": self.num_players,
            "is_end_state": self.is_end_state,
            "can_peel": self.can_peel(),
            "can_dump": self.can_dump(),
        }

