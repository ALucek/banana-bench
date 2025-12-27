"""Grid building and rendering utilities."""

from typing import Dict, Tuple, List, Set

from .models import WordEntry, Position, ValidationError


def compute_positions(entries: List[WordEntry]) -> Dict[str, Position]:
    """Compute the (x, y, direction) of each word's starting position."""
    positions: Dict[str, Position] = {}
    
    if not entries:
        return positions
    
    # Place root at origin
    root = entries[0]
    positions[root.word] = Position(0, 0, root.direction)
    
    # Process each subsequent word
    for entry in entries[1:]:
        if entry.target not in positions:
            continue  # Skip if target not found (error already reported)
        
        target_pos = positions[entry.target]
        
        # Find the absolute position of the shared letter in the target word
        shared_x = target_pos.x + (entry.target_idx if target_pos.direction == 'H' else 0)
        shared_y = target_pos.y + (entry.target_idx if target_pos.direction == 'V' else 0)
        
        # Compute where the new word starts based on shared letter position
        start_x = shared_x - (entry.word_idx if entry.direction == 'H' else 0)
        start_y = shared_y - (entry.word_idx if entry.direction == 'V' else 0)
        
        positions[entry.word] = Position(start_x, start_y, entry.direction)
    
    return positions


def build_grid(
    entries: List[WordEntry], 
    positions: Dict[str, Position]
) -> Tuple[Dict[Tuple[int, int], str], List[ValidationError]]:
    """Build the grid and check for conflicts."""
    grid: Dict[Tuple[int, int], str] = {}
    errors: List[ValidationError] = []
    
    for entry in entries:
        if entry.word not in positions:
            continue
        
        pos = positions[entry.word]
        
        for i, letter in enumerate(entry.word):
            cell = (pos.x + i, pos.y) if pos.direction == 'H' else (pos.x, pos.y + i)
            
            if cell in grid and grid[cell] != letter:
                errors.append(ValidationError(
                    code="GRID_CONFLICT",
                    message=f"Cell conflict at {cell}: existing '{grid[cell]}' vs new '{letter}' from '{entry.word}'",
                    word=entry.word
                ))
            grid[cell] = letter
    
    return grid, errors


def render_grid(grid: Dict[Tuple[int, int], str]) -> str:
    """Render the grid to a string."""
    if not grid:
        return ""
    
    min_x = min(pos[0] for pos in grid)
    max_x = max(pos[0] for pos in grid)
    min_y = min(pos[1] for pos in grid)
    max_y = max(pos[1] for pos in grid)
    
    lines = [
        ''.join(grid.get((x, y), '.') for x in range(min_x, max_x + 1))
        for y in range(min_y, max_y + 1)
    ]
    
    return '\n'.join(lines)


def extract_all_words_from_grid(grid: Dict[Tuple[int, int], str]) -> Set[str]:
    """Extract all horizontal and vertical words (2+ letters) from the grid."""
    if not grid:
        return set()
    
    words: Set[str] = set()
    
    min_x = min(pos[0] for pos in grid)
    max_x = max(pos[0] for pos in grid)
    min_y = min(pos[1] for pos in grid)
    max_y = max(pos[1] for pos in grid)
    
    # Extract horizontal words
    for y in range(min_y, max_y + 1):
        word = ""
        for x in range(min_x, max_x + 2):  # +2 to flush last word
            if (x, y) in grid:
                word += grid[(x, y)]
            else:
                if len(word) >= 2:
                    words.add(word)
                word = ""
    
    # Extract vertical words
    for x in range(min_x, max_x + 1):
        word = ""
        for y in range(min_y, max_y + 2):  # +2 to flush last word
            if (x, y) in grid:
                word += grid[(x, y)]
            else:
                if len(word) >= 2:
                    words.add(word)
                word = ""
    
    return words


def visualize(spec: str) -> str:
    """
    Quick visualization of a board specification.
    
    Parses the board and returns the rendered grid string.
    Raises ValueError if parsing fails.
    """
    from .parsing import parse_board
    
    entries, errors = parse_board(spec)
    
    if errors:
        raise ValueError(f"Parse errors: {[e.message for e in errors]}")
    
    if not entries:
        raise ValueError("Empty board specification")
    
    positions = compute_positions(entries)
    grid, grid_errors = build_grid(entries, positions)
    
    if grid_errors:
        raise ValueError(f"Grid errors: {[e.message for e in grid_errors]}")
    
    return render_grid(grid)

