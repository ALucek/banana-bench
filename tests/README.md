# Tests

Comprehensive test suite for banana-bench board verification.

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src

# Run specific test class
uv run pytest tests/test_verify.py::TestValidBoards -v

# Run specific test
uv run pytest tests/test_verify.py::TestParseErrors::test_empty_board -v
```

## Test Structure

| Test Class | Description |
|------------|-------------|
| `TestValidBoards` | Valid board configurations that should pass |
| `TestParseErrors` | Parsing failures (empty, malformed syntax) |
| `TestStructureErrors` | Structural validation (indices, letter match, direction) |
| `TestGridErrors` | Grid conflicts from overlapping letters |
| `TestWordValidation` | Dictionary word validation |
| `TestWarnings` | Warning cases (valid accidental words) |
| `TestValidationResult` | Result model structure verification |
| `TestEdgeCases` | Boundary conditions and edge cases |
| `TestGridRendering` | Grid output format validation |

## Test Coverage

### Parse Errors
- `EMPTY_BOARD` - Empty or whitespace-only specification
- `INVALID_ROOT` - Malformed root line (missing direction, invalid chars)
- `INVALID_LINE` - Malformed word placement lines

### Structure Errors
- `TARGET_NOT_FOUND` - Referenced target word doesn't exist
- `TARGET_INDEX_OOB` - Target index exceeds word length
- `WORD_INDEX_OOB` - Word index exceeds word length
- `LETTER_MISMATCH` - Letters at intersection don't match
- `SAME_DIRECTION` - Word not perpendicular to target

### Grid Errors
- `GRID_CONFLICT` - Different letters overlap on same cell

### Word Validation
- `INVALID_WORD` - Word not in TWL dictionary
- `ACCIDENTAL_INVALID` - Unintended invalid word formed on grid
- `ACCIDENTAL_VALID` - Unintended valid word formed (warning)