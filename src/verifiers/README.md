# Board Verification

Validates Banana-Bench board structures for correctness.

## Quick Start

```python
from src.verifiers import verify

result = verify("""
<board>
CAT H
TAR[0] @ CAT[2] V
</board>
""")

print(result.valid)    # True
print(result.words)    # ['CAT', 'TAR']
print(result.grid)     # Rendered grid
```

## API

### `verify(spec: str) -> ValidationResult`

Main verification function. Returns a `ValidationResult` with:

| Field | Type | Description |
|-------|------|-------------|
| `valid` | `bool` | True if board passes all checks |
| `errors` | `List[ValidationError]` | List of validation errors |
| `warnings` | `List[ValidationError]` | List of warnings |
| `words` | `List[str]` | Declared words on board |
| `grid` | `Optional[str]` | Rendered grid (if valid structure) |

### `validate_structure(entries: List[WordEntry]) -> List[ValidationError]`

Validates structural rules only (letter match, perpendicularity, index bounds).

### `validate_words(intended: List[str], grid_words: Set[str]) -> Tuple[List[ValidationError], List[ValidationError]]`

Validates words against TWL dictionary. Returns `(errors, warnings)`.

### `check_word(word: str) -> bool`

Check if a word exists in the TWL dictionary.

```python
from src.verifiers import check_word

check_word("cat")  # True (lowercase input)
```

## Error Codes

### Parse Errors

| Code | Description | Example |
|------|-------------|---------|
| `EMPTY_BOARD` | Board specification is empty | `<board></board>` |
| `INVALID_ROOT` | First line format invalid | `CAT` (missing direction) |
| `INVALID_LINE` | Word line format invalid | `DOG @ CAT V` (missing indices) |

### Structure Errors

| Code | Description | Example |
|------|-------------|---------|
| `TARGET_NOT_FOUND` | Target word not placed yet | `DOG[0] @ BIRD[0] V` when BIRD doesn't exist |
| `TARGET_INDEX_OOB` | Target index out of bounds | `DOG[0] @ CAT[5] V` (CAT has indices 0-2) |
| `WORD_INDEX_OOB` | Word index out of bounds | `DOG[5] @ CAT[0] V` (DOG has indices 0-2) |
| `LETTER_MISMATCH` | Intersection letters differ | `DOG[0] @ CAT[0] V` (D ≠ C) |
| `SAME_DIRECTION` | Not perpendicular | `DOG[0] @ CAT[0] H` when CAT is H |

### Grid Errors

| Code | Description | Example |
|------|-------------|---------|
| `GRID_CONFLICT` | Different letters on same cell | Overlapping words with mismatched letters |

### Word Errors

| Code | Description | Example |
|------|-------------|---------|
| `INVALID_WORD` | Word not in dictionary | `XYZZY H` |
| `ACCIDENTAL_INVALID` | Unintended invalid word on grid | Random letter sequence formed |
| `ACCIDENTAL_VALID` | Unintended valid word (warning) | Valid word formed by coincidence |

## Board Format

```
<board>
ROOT_WORD DIRECTION
WORD[j] @ TARGET[i] DIRECTION
...
</board>
```

- `DIRECTION`: `H` (horizontal) or `V` (vertical)
- `[j]`: Index in new word where intersection occurs (0-indexed)
- `[i]`: Index in target word where intersection occurs (0-indexed)
- Words must be perpendicular (H connects to V, V connects to H)
- Letters at intersection must match

## Example

```python
from src.verifiers import verify

# Valid board
result = verify("""
<board>
SCURRIES H
NINES[4] @ SCURRIES[0] V
</board>
""")
# NINES[4] = 'S', SCURRIES[0] = 'S' ✓
# SCURRIES is H, NINES is V ✓

# Invalid board
result = verify("""
<board>
CAT H
DOG[0] @ CAT[0] V
</board>
""")
# DOG[0] = 'D', CAT[0] = 'C' ✗ LETTER_MISMATCH
```

