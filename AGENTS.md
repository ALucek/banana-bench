# AGENTS.md

This file provides guidance to Coding Agents when working with code in this repository.

## Project Overview

Banana-Bench is an LLM benchmark based on Bananagrams, where language models play the word game by managing tiles, building valid crossword-style boards, and following game rules. The benchmark evaluates an LLM's ability to handle structured outputs, spatial reasoning, dictionary constraints, and multi-turn strategic decision-making.

## Core Architecture

### Three-Layer Design

The codebase is organized into three main layers:

1. **Game Layer** (`src/environment/game.py`): Manages the tile pool ("bunch"), tile distribution, and Bananagrams game rules (DUMP, PEEL operations). Handles the central game state independent of players.

2. **Player Layer** (`src/environment/player.py`): Manages individual player state (hand, board), coordinates LLM interaction via `LLMClient`, and parses LLM responses for actions and board specifications.

3. **Orchestrator Layer** (`src/environment/bananabench.py`): The top-level `BananaBench` class coordinates the game, players, turn order, board validation, and win conditions. Runs the complete benchmark loop.

### Verification System

The verifier (`src/verifiers/`) validates board specifications through a multi-stage pipeline:

- **Parsing** (`parsing.py`): Parses board specs into `WordEntry` objects
- **Structure Validation** (`verify.py`): Checks letter matches, perpendicularity, index bounds
- **Grid Construction** (`grid.py`): Builds 2D grid and detects overlapping letter conflicts
- **Word Validation** (`verify.py`): Validates all words against TWL dictionary and catches accidental words

Board specs use a custom XML-like format where the first line is the root word with direction (H/V), and subsequent lines specify how words connect to previously placed words.

### LLM Integration

Players interact with LLMs via the `LLMClient` class (`src/environment/llm_client.py`), which wraps LiteLLM for multi-provider support. The client maintains conversation history and handles completion requests. LLMs receive structured prompts (`src/environment/prompts/`) and must respond with XML-tagged output containing game plan, action, and board specification.

## Common Commands

### Development

```bash
# Install dependencies (uses uv package manager)
uv sync

# Run linter
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src

# Run specific test file
uv run pytest tests/test_verify.py -v

# Run specific test class
uv run pytest tests/test_verify.py::TestValidBoards -v

# Run specific test
uv run pytest tests/test_verify.py::TestParseErrors::test_empty_board -v
```

### Running Benchmarks

```bash
# Run benchmark with config file
python -m src.main configs/example.yaml

# Run with custom output path
python -m src.main configs/example.yaml --output results/my_run.json

# Run with verbose output
python -m src.main configs/example.yaml --verbose
```

## Configuration

Benchmarks are configured via YAML files in `configs/`. The config uses a player-based format that allows per-model kwargs:

```yaml
max_turns: 50
seed: 42  # optional, for reproducibility

players:
  - model: gpt-4o
    name: "GPT-4o Player"  # optional custom name
    temperature: 1.0
    max_tokens: 2048

  - model: claude-3-5-sonnet-20241022
    name: "Claude with Thinking"
    temperature: 0.7
    max_tokens: 4096
    # Provider-specific kwargs (passed to LiteLLM)
    thinking:
      type: enabled
      budget_tokens: 10000
```

**Key Features:**
- `num_players` is automatically set based on the `players` list
- Each player can have unique settings (model, temperature, max_tokens)
- Additional kwargs in player configs are passed directly to LiteLLM
- Supports all LiteLLM provider-specific parameters

## Key Validation Errors

When working with board verification, understand these error codes:

- **Parse Errors** (Level 0 - FATAL): `EMPTY_BOARD`, `INVALID_ROOT`, `INVALID_LINE`
- **Structure Errors** (Level 1 - CRITICAL): `TARGET_NOT_FOUND`, `TARGET_INDEX_OOB`, `WORD_INDEX_OOB`, `LETTER_MISMATCH`, `SAME_DIRECTION`
- **Grid Errors** (Level 2 - HIGH): `GRID_CONFLICT` (different letters overlap on same cell)
- **Word Errors** (Level 3 - MEDIUM): `INVALID_WORD`, `ACCIDENTAL_INVALID`, `ACCIDENTAL_VALID` (warning)
- **Tile Errors** (Level 4 - LOW): `TILES_NOT_IN_HAND` (error), `TILES_UNUSED` (warning)

### Cascading Error System

The validation system implements error cascading to prevent overwhelming LLMs with downstream errors:

**Filtering Rules** (applied in `_get_last_turn_feedback()`):
- Level 0 (FATAL) present → Show ONLY parsing errors
- Level 1 (CRITICAL) present → Show structural + INVALID_WORD + TILES_NOT_IN_HAND (hide grid conflicts and accidental words)
- Level 2 (HIGH) present → Show grid + all word + tile errors
- Otherwise → Show all errors (limited to max 5)
- Warnings (TILES_UNUSED, ACCIDENTAL_VALID) are always shown separately

**Key Implementation Files**:
- `src/verifiers/cascade.py` - Core filtering logic with `filter_cascading_errors()`
- `src/verifiers/models.py` - `ValidationError.cascade_level` field
- `src/environment/bananabench.py` - Filtering applied in `_get_last_turn_feedback()`

**Important**: All errors are still collected in `ValidationResult.errors` for debugging and tests. Filtering only occurs when presenting feedback to the LLM.

## Game Flow

1. `BananaBench.create()` initializes game with tile pool and creates players with LLM clients
2. `setup()` deals starting hands to all players
3. Main loop in `run()` or manual `step()` calls:
   - Build prompt with current game state and feedback from last turn
   - LLM generates response with game plan, action, and board spec
   - Parse response and validate board
   - Auto-PEEL if valid board uses all tiles (everyone draws one)
   - Auto-BANANAS (win) if valid board uses all tiles and bunch is depleted
   - Process explicit DUMP action if needed
4. Game ends when player wins or max turns reached

## Board Specification Format

Example board spec:
```
HELLO H
WORLD HELLO 4 0 V
```

Format: `WORD TARGET TARGET_IDX WORD_IDX DIRECTION`
- First line: `ROOT_WORD DIRECTION`
- Direction: `H` (horizontal) or `V` (vertical)
- Indices are 0-based positions where words intersect
- Words must be perpendicular to their target
- Letters at intersection must match

## Results

Benchmark results are saved as JSON to `results/` (gitignored) containing:
- Full configuration
- Turn-by-turn history with validations
- Complete conversation history for each player
- Final game state and outcome
- Timing information
