"""Board verification for banana-bench."""

from .verify import verify, validate_structure, validate_words
from .models import WordEntry, Position, ValidationError, ValidationResult
from .parsing import parse_board, extract_board_content
from .grid import compute_positions, build_grid, render_grid, extract_all_words_from_grid, visualize
from .data import check_word

__all__ = [
    # Main verification
    "verify",
    "validate_structure", 
    "validate_words",
    # Models
    "WordEntry",
    "Position",
    "ValidationError",
    "ValidationResult",
    # Parsing
    "parse_board",
    "extract_board_content",
    # Grid utilities
    "compute_positions",
    "build_grid",
    "render_grid",
    "extract_all_words_from_grid",
    "visualize",
    # Dictionary
    "check_word",
]
