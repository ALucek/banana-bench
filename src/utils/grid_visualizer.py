import re
from typing import Dict, Tuple, List

def parse_board(spec: str) -> List[dict]:
    """Parse the board specification into a list of word entries."""
    lines = [line.strip() for line in spec.strip().split('\n') if line.strip()]
    entries = []
    
    # First line: ROOT DIRECTION
    root_match = re.match(r'^(\w+)\s+([HV])$', lines[0])
    if not root_match:
        raise ValueError(f"Invalid root line: {lines[0]}")
    
    entries.append({
        'word': root_match.group(1),
        'direction': root_match.group(2),
        'target': None,
        'target_idx': None,
        'word_idx': None
    })
    
    # Subsequent lines: WORD[j] @ TARGET[i] DIRECTION
    pattern = r'^(\w+)\[(\d+)\]\s*@\s*(\w+)\[(\d+)\]\s+([HV])$'
    for line in lines[1:]:
        match = re.match(pattern, line)
        if not match:
            raise ValueError(f"Invalid line: {line}")
        
        entries.append({
            'word': match.group(1),
            'word_idx': int(match.group(2)),
            'target': match.group(3),
            'target_idx': int(match.group(4)),
            'direction': match.group(5)
        })
    
    return entries

def compute_positions(entries: List[dict]) -> Dict[str, Tuple[int, int, str]]:
    """Compute the (x, y, direction) of each word's starting position."""
    positions = {}
    
    # Place root at origin
    root = entries[0]
    positions[root['word']] = (0, 0, root['direction'])
    
    # Process each subsequent word
    for entry in entries[1:]:
        word = entry['word']
        target = entry['target']
        target_idx = entry['target_idx']
        word_idx = entry['word_idx']
        direction = entry['direction']
        
        if target not in positions:
            raise ValueError(f"Target word '{target}' not yet placed when placing '{word}'")
        
        target_x, target_y, target_dir = positions[target]
        
        # Find the absolute position of the shared letter in the target word
        if target_dir == 'H':
            shared_x = target_x + target_idx
            shared_y = target_y
        else:  # V
            shared_x = target_x
            shared_y = target_y + target_idx
        
        # Compute where the new word starts based on shared letter position
        if direction == 'H':
            start_x = shared_x - word_idx
            start_y = shared_y
        else:  # V
            start_x = shared_x
            start_y = shared_y - word_idx
        
        positions[word] = (start_x, start_y, direction)
    
    return positions

def render_grid(entries: List[dict], positions: Dict[str, Tuple[int, int, str]]) -> str:
    """Render the board to a string grid."""
    grid = {}
    errors = []
    
    # Place each word on the grid
    for entry in entries:
        word = entry['word']
        x, y, direction = positions[word]
        
        for i, letter in enumerate(word):
            if direction == 'H':
                pos = (x + i, y)
            else:
                pos = (x, y + i)
            
            if pos in grid:
                if grid[pos] != letter:
                    errors.append(f"Conflict at {pos}: '{grid[pos]}' vs '{letter}' (from {word})")
            else:
                grid[pos] = letter
    
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
    
    # Find grid bounds
    min_x = min(pos[0] for pos in grid)
    max_x = max(pos[0] for pos in grid)
    min_y = min(pos[1] for pos in grid)
    max_y = max(pos[1] for pos in grid)
    
    # Render to string
    lines = []
    for y in range(min_y, max_y + 1):
        row = ''
        for x in range(min_x, max_x + 1):
            row += grid.get((x, y), '.')
        lines.append(row)
    
    return '\n'.join(lines)

def visualize(spec: str) -> str:
    """Main function: parse and visualize a board spec."""
    entries = parse_board(spec)
    positions = compute_positions(entries)
    return render_grid(entries, positions)


if __name__ == '__main__':
    # Test with the example
    example = """
SCURRIES H
NINES[4] @ SCURRIES[0] V
RUNES[2] @ NINES[0] H
YEN[2] @ NINES[2] H
BRAWN[1] @ SCURRIES[3] V
DEN[2] @ BRAWN[4] H
DEED[0] @ DEN[0] V
STIR[2] @ SCURRIES[5] V
SPARK[0] @ STIR[0] H
TRAPS[2] @ SPARK[2] V
TIGER[0] @ TRAPS[0] H
TAROT[2] @ TIGER[4] V
"""
    
    print("Input spec:")
    print(example)
    print("\nRendered grid:")
    print(visualize(example))