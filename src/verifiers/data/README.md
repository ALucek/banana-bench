# Data Sources

Reference data and lookup utilities for banana-bench.

## TWL Dictionary

The Tournament Word List (TWL06) is the official Scrabble dictionary used for word validation.

### Usage

```python
from src.data import check_word

# Check if a word is valid (case-insensitive)
check_word("cat")      # True
check_word("CAT")      # True
check_word("xyzzy")    # False
```

### Implementation

- `twl.py` - DAWG (Directed Acyclic Word Graph) implementation for efficient lookups
- `twl_data.bin` - Compressed binary data containing the TWL06 dictionary

### Performance

- **Lookup time**: O(k) where k is the length of the word
- **Memory**: ~500KB compressed binary
- **Dictionary size**: ~178,000 words

### Credits

Original implementation from [github.com/fogleman/TWL06](https://github.com/fogleman/TWL06)

