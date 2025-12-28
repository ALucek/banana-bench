"""
Board verification module for validating Bananagrams board structures.

Validates:
1. Structural rules (letter match, perpendicularity, index bounds, target ordering)
2. Grid conflicts (overlapping cells must have matching letters)
3. Word validity (all words must be in the TWL dictionary)
4. No accidental words (all 2+ letter sequences on grid must be intentional valid words)
"""

from typing import Dict, List, Tuple, Set

from .models import WordEntry, ValidationError, ValidationResult
from .parsing import parse_board
from .grid import compute_positions, build_grid, render_grid, extract_all_words_from_grid
from .data import check_word as is_valid_word


def validate_structure(entries: List[WordEntry]) -> List[ValidationError]:
    """Validate structural rules: letter match, perpendicularity, index bounds, target ordering."""
    errors: List[ValidationError] = []
    placed_words: Dict[str, WordEntry] = {}
    
    if not entries:
        return errors
    
    # Root word
    root = entries[0]
    placed_words[root.word] = root
    
    for i, entry in enumerate(entries[1:], start=2):
        # Check target exists
        if entry.target not in placed_words:
            errors.append(ValidationError(
                code="TARGET_NOT_FOUND",
                message=f"Target word '{entry.target}' not placed before '{entry.word}'",
                word=entry.word,
                line=i,
                cascade_level=1  # CRITICAL
            ))
            continue
        
        target_entry = placed_words[entry.target]
        
        # Check index bounds for target
        if entry.target_idx >= len(entry.target):
            errors.append(ValidationError(
                code="TARGET_INDEX_OOB",
                message=f"Target index {entry.target_idx} out of bounds for '{entry.target}' (length {len(entry.target)})",
                word=entry.word,
                line=i,
                cascade_level=1  # CRITICAL
            ))
            continue
        
        # Check index bounds for word
        if entry.word_idx >= len(entry.word):
            errors.append(ValidationError(
                code="WORD_INDEX_OOB",
                message=f"Word index {entry.word_idx} out of bounds for '{entry.word}' (length {len(entry.word)})",
                word=entry.word,
                line=i,
                cascade_level=1  # CRITICAL
            ))
            continue
        
        # Check letter match
        target_letter = entry.target[entry.target_idx]
        word_letter = entry.word[entry.word_idx]
        if target_letter != word_letter:
            errors.append(ValidationError(
                code="LETTER_MISMATCH",
                message=(
                    f"Letter mismatch: {entry.word}[{entry.word_idx}]='{word_letter}' vs "
                    f"{entry.target}[{entry.target_idx}]='{target_letter}'. "
                    f"TIP: {entry.word} should share the letter '{target_letter}' at position "
                    f"{entry.word_idx}, not '{word_letter}'."
                ),
                word=entry.word,
                line=i,
                cascade_level=1  # CRITICAL
            ))
        
        # Check perpendicularity
        if entry.direction == target_entry.direction:
            errors.append(ValidationError(
                code="SAME_DIRECTION",
                message=f"'{entry.word}' must be perpendicular to '{entry.target}' (both are {entry.direction})",
                word=entry.word,
                line=i,
                cascade_level=1  # CRITICAL
            ))
        
        placed_words[entry.word] = entry
    
    return errors


def validate_words(
    intended_words: List[str], 
    grid_words: Set[str]
) -> Tuple[List[ValidationError], List[ValidationError]]:
    """Validate all words against the dictionary and check for accidental words."""
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    
    intended_set = set(intended_words)
    
    # Check intended words are valid (TWL uses lowercase)
    for word in intended_words:
        if not is_valid_word(word.lower()):
            errors.append(ValidationError(
                code="INVALID_WORD",
                message=f"'{word}' is not a valid dictionary word",
                word=word,
                cascade_level=3  # MEDIUM
            ))
    
    # Check for accidental words (words on grid that weren't intended)
    accidental_words = grid_words - intended_set
    for word in accidental_words:
        if not is_valid_word(word.lower()):
            errors.append(ValidationError(
                code="ACCIDENTAL_INVALID",
                message=f"Accidental word '{word}' on grid is not a valid dictionary word",
                word=word,
                cascade_level=3  # MEDIUM
            ))
        else:
            warnings.append(ValidationError(
                code="ACCIDENTAL_VALID",
                message=f"Accidental word '{word}' formed on grid (valid, but not declared)",
                word=word,
                cascade_level=3  # MEDIUM
            ))
    
    return errors, warnings


def verify(spec: str) -> ValidationResult:
    """
    Main verification function: validates a board specification.
    
    Returns a ValidationResult with:
    - valid: True if the board passes all checks
    - errors: List of validation errors
    - warnings: List of warnings (e.g., valid accidental words)
    - words: List of words on the board
    - grid: Rendered grid string (if structurally valid)
    """
    all_errors: List[ValidationError] = []
    all_warnings: List[ValidationError] = []
    
    # Parse the board
    entries, parse_errors = parse_board(spec)
    all_errors.extend(parse_errors)
    
    if not entries:
        return ValidationResult(
            valid=False,
            errors=all_errors
        )
    
    # Validate structure
    structure_errors = validate_structure(entries)
    all_errors.extend(structure_errors)
    
    # Compute positions and build grid
    positions = compute_positions(entries)
    grid, grid_errors = build_grid(entries, positions)
    all_errors.extend(grid_errors)
    
    # Extract all words from grid
    intended_words = [e.word for e in entries]
    grid_words = extract_all_words_from_grid(grid)
    
    # Validate words
    word_errors, word_warnings = validate_words(intended_words, grid_words)
    all_errors.extend(word_errors)
    all_warnings.extend(word_warnings)
    
    # Render grid if no structural errors
    rendered_grid = render_grid(grid) if grid else None
    
    # Count tiles used and extract letters (from grid cells)
    tiles_used = len(grid) if grid else 0
    letters_used = sorted(grid.values()) if grid else []
    
    return ValidationResult(
        valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
        words=intended_words,
        grid=rendered_grid,
        tiles_used=tiles_used,
        letters_used=letters_used,
    )