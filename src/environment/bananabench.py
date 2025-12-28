import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from pydantic import BaseModel, Field, ConfigDict

from .game import Game
from .player import Player, TurnResult, Action
from .prompts import SYSTEM_PROMPT, build_player_prompt
from ..verifiers.models import ValidationError


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


class BananaBench(BaseModel):
    """
    Top-level orchestrator for Bananagrams benchmarks.
    
    Coordinates players and the game, manages turn order,
    and handles game completion logic.
    
    Attributes:
        game: The Game instance managing tile pool
        players: List of Player instances
        config: Benchmark configuration
        turn_history: History of all turns
        current_turn: Current turn number
        is_complete: Whether the benchmark has finished
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    game: Optional[Game] = None
    players: List[Player] = Field(default_factory=list)
    config: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    turn_history: List[TurnResult] = Field(default_factory=list)
    current_turn: int = 0
    is_complete: bool = False
    winner: Optional[str] = None
    end_reason: str = ""
    started_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        config: Optional[BenchmarkConfig] = None,
        **config_kwargs: Any
    ) -> "BananaBench":
        """
        Factory method to create a benchmark with configured game and players.
        
        Args:
            config: Optional BenchmarkConfig instance
            **config_kwargs: Config parameters if config not provided
            
        Returns:
            Configured BananaBench instance
        """
        if config is None:
            config = BenchmarkConfig(**config_kwargs)
        
        # Create the game
        game = Game.create(num_players=config.num_players, seed=config.seed)

        # Create players from player configs
        players = []
        for i in range(config.num_players):
            # Cycle through player configs if fewer than num_players
            player_config = config.players[i % len(config.players)]

            # Determine player name
            player_name = player_config.name or f"Player {i+1} ({player_config.model})"

            # Extract base kwargs
            llm_kwargs = {
                "temperature": player_config.temperature,
                "max_tokens": player_config.max_tokens,
            }

            # Add any extra kwargs from player config (e.g., thinking params for Claude)
            if hasattr(player_config, '__pydantic_extra__') and player_config.__pydantic_extra__:
                llm_kwargs.update(player_config.__pydantic_extra__)

            player = Player.create(
                player_id=f"p{i+1}",
                model=player_config.model,
                name=player_name,
                **llm_kwargs
            )
            players.append(player)

        return cls(game=game, players=players, config=config)
    
    def setup(self) -> None:
        """
        Initialize the game by dealing starting hands to all players.
        """
        if self.game is None:
            raise ValueError("Game not initialized")
        
        for player in self.players:
            starting_hand = self.game.draw_starting_hand()
            player.set_starting_hand(starting_hand)
        
        self.started_at = datetime.now()
        self.current_turn = 0
        self.is_complete = False
        self.winner = None
        self.end_reason = ""
        self.turn_history = []
    
    def get_current_player(self) -> Player:
        """Get the player whose turn it is."""
        player_idx = self.current_turn % len(self.players)
        return self.players[player_idx]
    
    def process_action(self, player: Player, action: Action, dump_tile: Optional[str] = None) -> Optional[str]:
        """
        Process a player's action.
        
        Args:
            player: The player taking the action
            action: The action type
            dump_tile: Tile to dump if action is DUMP
            
        Returns:
            Error message if action failed, None if successful
        """
        if self.game is None:
            return "Game not initialized"
        
        if action == "DUMP":
            if dump_tile is None:
                return "DUMP requires a tile to return"
            
            if not player.has_tile(dump_tile):
                return f"Cannot DUMP '{dump_tile}' - not in hand"
            
            if not self.game.can_dump():
                return "Cannot DUMP - not enough tiles in bunch"
            
            # Remove the tile and get 3 new ones
            player.remove_tile(dump_tile)
            new_tiles = self.game.dump(dump_tile)
            player.add_tiles(new_tiles)
            
        return None
    
    def check_winner(self, player: Player, validation_valid: bool) -> bool:
        """
        Check if a player has won.
        
        Args:
            player: The player to check
            validation_valid: Whether their board validation passed
            
        Returns:
            True if the player has won
        """
        if self.game is None:
            return False
        
        # Win condition: BANANAS called, board is valid, end state reached
        if self.game.is_end_state and validation_valid and player.tiles_in_hand == 0:
            self.winner = player.player_id
            self.is_complete = True
            self.end_reason = f"{player.name} called BANANAS with valid board"
            return True
        
        return False
    
    def check_max_turns(self) -> bool:
        """Check if max turns reached."""
        if self.current_turn >= self.config.max_turns:
            self.is_complete = True
            self.end_reason = f"Max turns ({self.config.max_turns}) reached"
            return True
        return False
    
    def record_turn(self, turn_result: TurnResult) -> None:
        """Record a turn result in history."""
        self.turn_history.append(turn_result)
        self.current_turn += 1
    
    def get_state(self) -> Dict:
        """
        Get the current benchmark state.
        
        Returns:
            Dictionary containing benchmark state
        """
        return {
            "current_turn": self.current_turn,
            "is_complete": self.is_complete,
            "winner": self.winner,
            "end_reason": self.end_reason,
            "game_state": self.game.get_state() if self.game else None,
            "players": [p.get_state() for p in self.players],
            "num_turns_recorded": len(self.turn_history),
        }
    
    def get_result(self) -> BenchmarkResult:
        """
        Get the final benchmark result.
        
        Returns:
            BenchmarkResult containing full run data
        """
        ended_at = datetime.now()
        duration = (ended_at - self.started_at).total_seconds() if self.started_at else 0.0
        
        # Collect conversation history from all players
        conversation_history = {}
        for player in self.players:
            if player.llm_client:
                conversation_history[player.player_id] = player.llm_client.get_messages()
        
        return BenchmarkResult(
            config=self.config,
            winner=self.winner,
            total_turns=self.current_turn,
            end_reason=self.end_reason,
            player_results={p.player_id: p.get_state() for p in self.players},
            turn_history=self.turn_history,
            game_state=self.game.get_state() if self.game else {},
            conversation_history=conversation_history,
            started_at=self.started_at.isoformat() if self.started_at else "",
            ended_at=ended_at.isoformat(),
            duration_seconds=duration,
        )
    
    def save_result(self, path: str | Path) -> None:
        """
        Save the benchmark result to a JSON file.
        
        Args:
            path: Path to save the result file
        """
        result = self.get_result()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
    
    def _get_last_turn_feedback(self, player: Player) -> Dict[str, Any]:
        """Get feedback from the player's last turn."""
        from ..verifiers.cascade import filter_cascading_errors

        # Find the player's most recent turn
        for turn in reversed(self.turn_history):
            if turn.player_id == player.player_id:
                # Filter cascading errors
                filtered_errors = None
                if turn.validation and turn.validation.errors:
                    filtered_errors = filter_cascading_errors(turn.validation.errors)

                # Get rendered grid if available
                rendered_grid = None
                if turn.validation and turn.validation.grid:
                    rendered_grid = turn.validation.grid

                return {
                    "validation_errors": [e.message for e in filtered_errors] if filtered_errors else None,
                    "validation_warnings": [w.message for w in turn.validation.warnings] if turn.validation else None,
                    "action_error": turn.error,
                    "last_action": turn.action,
                    "rendered_grid": rendered_grid,
                }
        return {}
    
    def step(self, player: Optional[Player] = None) -> TurnResult:
        """
        Execute a single turn for a player.
        
        Prompts the LLM, parses the response, validates the board,
        and processes the action.
        
        Args:
            player: The player to step (defaults to current player)
            
        Returns:
            TurnResult containing the turn outcome
        """
        if self.game is None:
            raise ValueError("Game not initialized. Call setup() first.")
        
        if self.is_complete:
            raise ValueError("Benchmark is already complete")
        
        if player is None:
            player = self.get_current_player()
        
        if player.llm_client is None:
            raise ValueError(f"Player {player.player_id} has no LLM client")
        
        tiles_before = player.hand.copy()
        turn_number = self.current_turn + 1
        
        # Build the prompt with feedback from last turn
        feedback = self._get_last_turn_feedback(player)
        prompt = build_player_prompt(
            hand=player.hand,
            tiles_in_bunch=self.game.tiles_remaining,
            num_players=self.game.num_players,
            is_end_state=self.game.is_end_state,
            turn_number=turn_number,
            current_board=player.board_spec,
            **feedback
        )
        
        # Add system prompt if this is the first message
        if not player.llm_client.messages:
            player.llm_client.add_message("system", SYSTEM_PROMPT)
        
        # Add user prompt and get completion
        player.llm_client.add_message("user", prompt)
        
        try:
            response = player.llm_client.completion()
            raw_response = response.choices[0].message.content or ""
        except Exception as e:
            # Handle LLM errors gracefully
            raw_response = ""
            error = f"LLM error: {str(e)}"
            turn_result = TurnResult(
                player_id=player.player_id,
                turn_number=turn_number,
                action="NONE",
                tiles_before=tiles_before,
                tiles_after=player.hand.copy(),
                raw_response=raw_response,
                error=error,
            )
            self.record_turn(turn_result)
            player.turn_count += 1
            return turn_result
        
        # Add assistant response to history
        player.llm_client.add_message("assistant", raw_response)
        
        # Parse the response
        parsed = Player.parse_response(raw_response)
        
        # Validate board if provided
        validation = None
        auto_peeled = False
        auto_bananas = False
        if parsed.board:
            validation = player.validate_board(parsed.board)
            player.board_spec = parsed.board
            player.last_validation = validation
            
            # Check if board uses exactly the tiles in hand
            board_letters = sorted(validation.letters_used)
            hand_letters = sorted(player.hand)
            tiles_match = board_letters == hand_letters
            uses_all_tiles = validation.tiles_used == player.tiles_in_hand
            
            # Add tile mismatch errors if applicable
            if not tiles_match:
                from collections import Counter
                board_count = Counter(board_letters)
                hand_count = Counter(hand_letters)
                
                missing = board_count - hand_count  # Used but don't have
                unused = hand_count - board_count  # Have but didn't use
                
                if missing:
                    validation.errors.append(ValidationError(
                        code="TILES_NOT_IN_HAND",
                        message=f"Board uses tiles not in hand: {dict(missing)}",
                        cascade_level=4  # LOW
                    ))
                    validation.valid = False

                if unused:
                    validation.warnings.append(ValidationError(
                        code="TILES_UNUSED",
                        message=f"Tiles in hand not used: {dict(unused)}",
                        cascade_level=4  # LOW
                    ))
            
            # Check if board is valid and uses exactly all tiles correctly
            if validation.valid and tiles_match and uses_all_tiles:
                # Auto-BANANAS: if end state (bunch depleted), player wins!
                if self.game.is_end_state:
                    auto_bananas = True
                    self.winner = player.player_id
                    self.is_complete = True
                    self.end_reason = f"{player.name} wins with BANANAS!"
                # Auto-PEEL: if bunch has tiles, everyone draws
                elif self.game.can_peel():
                    peel_tiles = self.game.peel()
                    for i, p in enumerate(self.players):
                        p.add_tiles([peel_tiles[i]])
                    auto_peeled = True
        
        # Process explicit actions (DUMP only now)
        action_error = None
        if not auto_peeled and not auto_bananas:
            action_error = self.process_action(player, parsed.action, parsed.dump_tile)
        
        # Build turn result
        turn_result = TurnResult(
            player_id=player.player_id,
            turn_number=turn_number,
            action=parsed.action,
            dump_tile=parsed.dump_tile,
            board_spec=parsed.board,
            validation=validation,
            thinking=parsed.thinking,
            tiles_before=tiles_before,
            tiles_after=player.hand.copy(),
            raw_response=raw_response,
            error=action_error,
            auto_peeled=auto_peeled,
            auto_bananas=auto_bananas,
        )
        
        self.record_turn(turn_result)
        player.turn_count += 1
        
        # Check max turns
        self.check_max_turns()
        
        return turn_result
    
    def run(
        self,
        on_turn: Optional[Callable[[TurnResult], None]] = None,
        verbose: bool = False,
    ) -> BenchmarkResult:
        """
        Run the full benchmark until completion.
        
        Args:
            on_turn: Optional callback called after each turn
            verbose: If True, print progress to stdout
            
        Returns:
            BenchmarkResult containing the full run data
        """
        if self.game is None:
            self.setup()
        elif not self.started_at:
            self.setup()
        
        if verbose:
            print(f"Starting benchmark with {len(self.players)} players")
            print(f"Max turns: {self.config.max_turns}")
            print(f"Tiles in bunch: {self.game.tiles_remaining}")
            print("-" * 40)
        
        while not self.is_complete:
            player = self.get_current_player()
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"Turn {self.current_turn + 1}: {player.name}")
                print(f"Hand ({player.tiles_in_hand}): {' '.join(sorted(player.hand))}")
                print(f"Bunch: {self.game.tiles_remaining} tiles")
                print("-" * 60)
                print("Calling LLM...", end=" ", flush=True)
            
            turn_result = self.step(player)
            
            if verbose:
                print("done.\n")
                
                # Show game plan/thinking
                if turn_result.thinking:
                    print("Game Plan:")
                    print(turn_result.thinking)
                    print()
                
                # Show action
                action_str = f"Action: {turn_result.action}"
                if turn_result.dump_tile:
                    action_str += f" {turn_result.dump_tile}"
                print(action_str)
                
                # Show error or board
                if turn_result.error:
                    print(f"❌ ERROR: {turn_result.error}")
                elif turn_result.board_spec:
                    print("\nBoard Spec:")
                    print(turn_result.board_spec)
                    
                    if turn_result.validation:
                        if turn_result.validation.grid:
                            print("\nRendered Grid:")
                            print(turn_result.validation.grid)
                        
                        # Validation status
                        if turn_result.validation.valid:
                            print("\n✓ Board is valid")
                        else:
                            print(f"\n✗ Board has {len(turn_result.validation.errors)} errors:")
                            for err in turn_result.validation.errors[:3]:  # Show first 3
                                print(f"  - {err.message}")
                            if len(turn_result.validation.errors) > 3:
                                print(f"  ... and {len(turn_result.validation.errors) - 3} more")
                        
                        if turn_result.validation.warnings:
                            print(f"\n⚠ {len(turn_result.validation.warnings)} warnings:")
                            for warn in turn_result.validation.warnings[:3]:
                                print(f"  - {warn.message}")
                            if len(turn_result.validation.warnings) > 3:
                                print(f"  ... and {len(turn_result.validation.warnings) - 3} more")
                
                # Show auto-peel or auto-bananas
                if turn_result.auto_bananas:
                    print(f"\n*** BANANAS! {player.name} WINS! ***")
                elif turn_result.auto_peeled:
                    print(f"\nAUTO-PEEL! All tiles used. Everyone draws a tile.")
                    print(f"New tile: {turn_result.tiles_after[-1] if turn_result.tiles_after else '?'}")
            
            if on_turn:
                on_turn(turn_result)
        
        if verbose:
            print("-" * 40)
            print(f"Benchmark complete: {self.end_reason}")
            if self.winner:
                print(f"Winner: {self.winner}")
            
            # Print final boards
            print("\n=== Final Boards ===")
            for player in self.players:
                print(f"\n{player.name}:")
                if player.board_spec:
                    print(player.board_spec)
                    if player.last_validation and player.last_validation.grid:
                        print("\nRendered Grid:")
                        print(player.last_validation.grid)
                    if player.last_validation:
                        status = "✓ Valid" if player.last_validation.valid else "✗ Invalid"
                        print(f"Status: {status}")
                        if player.last_validation.errors:
                            print(f"Errors: {len(player.last_validation.errors)}")
                else:
                    print("  (no board)")
        
        return self.get_result()
