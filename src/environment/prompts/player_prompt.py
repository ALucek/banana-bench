from typing import Dict, List, Optional


def format_hand(hand: List[str]) -> str:
    """Format hand as sorted letters with counts."""
    counts: Dict[str, int] = {}
    for tile in hand:
        counts[tile] = counts.get(tile, 0) + 1
    
    parts = [f"{letter}:{count}" for letter, count in sorted(counts.items())]
    return " ".join(parts)


def format_feedback(
    validation_errors: Optional[List[str]] = None,
    validation_warnings: Optional[List[str]] = None,
    action_error: Optional[str] = None,
) -> str:
    """Format feedback from the previous turn."""
    lines = []
    
    if action_error:
        lines.append(f"Action failed: {action_error}")
    
    if validation_errors:
        lines.append("Board errors:")
        for err in validation_errors:
            lines.append(f"  - {err}")
    
    if validation_warnings:
        lines.append("Warnings:")
        for warn in validation_warnings:
            lines.append(f"  - {warn}")
    
    if not lines:
        return ""
    
    return "\n".join(lines)


def build_player_prompt(
    hand: List[str],
    tiles_in_bunch: int,
    num_players: int,
    is_end_state: bool,
    turn_number: int,
    current_board: Optional[str] = None,
    rendered_grid: Optional[str] = None,
    last_action: Optional[str] = None,
    validation_errors: Optional[List[str]] = None,
    validation_warnings: Optional[List[str]] = None,
    action_error: Optional[str] = None,
) -> str:
    """
    Build the player prompt with current game state and feedback.

    Args:
        hand: Current tiles in hand
        tiles_in_bunch: Tiles remaining in the bunch
        num_players: Number of players
        is_end_state: Whether BANANAS can be called
        turn_number: Current turn number
        current_board: Player's current board spec (if any)
        rendered_grid: Rendered visual grid of the board (if any)
        last_action: The action attempted last turn
        validation_errors: Errors from last board validation
        validation_warnings: Warnings from last validation
        action_error: Error from last action attempt

    Returns:
        Formatted prompt string
    """
    lines = []
    
    # Turn info
    lines.append(f"## Turn {turn_number}")
    lines.append("")
    
    # Feedback from previous turn
    feedback = format_feedback(validation_errors, validation_warnings, action_error)
    if feedback:
        lines.append("### Feedback from last turn")
        lines.append(feedback)
        lines.append("")
    
    # Current state
    lines.append("### Your Hand")
    lines.append(f"Tiles ({len(hand)}): {format_hand(hand)}")
    lines.append(f"Letters: {' '.join(sorted(hand))}")
    lines.append("")
    
    # Game state
    lines.append("### Game State")
    lines.append(f"- Bunch: {tiles_in_bunch} tiles remaining")
    lines.append(f"- Players: {num_players}")
    
    if is_end_state:
        lines.append("- **BANANAS available!** Bunch is depleted. Use all tiles to win!")
    else:
        lines.append(f"- PEEL will give everyone 1 tile (need {num_players} in bunch)")
    
    lines.append("")
    
    # Current board if exists
    if current_board:
        lines.append("### Your Current Board")

        # Show rendered grid if available
        if rendered_grid:
            lines.append("Visual grid:")
            lines.append("```")
            lines.append(rendered_grid)
            lines.append("```")
            lines.append("")

        # Show board specification
        lines.append("Board specification:")
        lines.append("```")
        lines.append(current_board)
        lines.append("```")
        lines.append("")

    # Instructions
    # lines.append("### Instructions")
    # lines.append("Build a valid crossword grid using ALL your tiles.")
    # lines.append("When valid and complete, PEEL happens automatically and you'll get a new tile.")
    # lines.append("Use DUMP X to exchange a difficult letter. Winning is automatic when bunch is empty!")
    # lines.append("Respond with <game_plan>, <action>, and <board> tags.")

    return "\n".join(lines)

