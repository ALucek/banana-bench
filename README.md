# Banana-Bench

<img src="./bb-logo.png" width=300>

A benchmark for evaluating Large Language Models through the game of Bananagrams. LLMs must build valid crossword-style boards using structured output formats, demonstrating spatial reasoning, constraint satisfaction, and multi-turn strategic decision-making.

## Features

- **LLM-Driven Gameplay**: Models play Bananagrams by generating valid board configurations
- **Structured Validation**: Comprehensive verification system with cascading error feedback
- **Multi-Provider Support**: Works with any LLM via LiteLLM (OpenAI, Anthropic, etc.)
- **Detailed Tracking**: Full conversation history and turn-by-turn analysis
- **Smart Error Filtering**: Cascading error system prevents overwhelming models with downstream errors
- **Visual Feedback**: Rendered grid visualization helps models understand board state

## Setup and Install

### Requirements
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/banana-bench.git
cd banana-bench

# Install dependencies with uv
uv sync

# Set up your LLM API key (for OpenAI, Anthropic, etc.)
export OPENAI_API_KEY="your-api-key"
# or
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Quick Start

```bash
# Run a benchmark with the example config
uv run python -m src.main configs/example.yaml

# Run with verbose output to see the game play out
uv run python -m src.main configs/example.yaml --verbose

# Save results to a specific location
uv run python -m src.main configs/example.yaml --output results/my_run.json
```

### Configuration

Create a YAML config file to customize your benchmark:

**Basic Example:**
```yaml
max_turns: 50
seed: 42

players:
  - model: gpt-4o
    temperature: 1.0
    max_tokens: 2048

  - model: claude-3-5-sonnet
    temperature: 1.0
    max_tokens: 2048
```

**Advanced Example** (per-player kwargs, custom names, provider-specific params):
```yaml
max_turns: 50
seed: 42

players:
  - model: gpt-4o
    name: "GPT-4o Aggressive"
    temperature: 1.2
    max_tokens: 2048

  - model: claude-3-5-sonnet-20241022
    name: "Claude with Extended Thinking"
    temperature: 0.7
    max_tokens: 4096
    # Claude-specific: extended thinking
    thinking:
      type: enabled
      budget_tokens: 10000

  - model: gpt-4o-mini
    name: "Deterministic Player"
    temperature: 0.0
    max_tokens: 1024
```

**Key Features:**
- Each player can have different model, temperature, and max_tokens
- Pass provider-specific kwargs (like Claude's `thinking` parameter)
- Mix and match any LiteLLM-supported parameters
- Optional custom names for better result tracking
- Number of players is automatically determined by the players list

## How It Works

### Game Flow

1. **Setup**: Each player receives a starting hand of tiles (21 for 1-4 players)
2. **Turn Loop**: On each turn:
   - LLM receives current hand, game state, and feedback from previous turn
   - LLM generates a board specification
   - Board is validated against structure rules, grid conflicts, and dictionary
   - **Auto-PEEL**: If board is valid and uses all tiles, everyone draws one tile
   - **Auto-BANANAS**: If bunch is empty and board is valid, player wins!
3. **Actions**: Players can use `DUMP X` to exchange a difficult tile for three new ones

### Validation System

The verifier checks boards through multiple stages:

1. **Parsing**: Board format must be correct
2. **Structure**: Letter matches, perpendicularity, index bounds
3. **Grid**: No overlapping letter conflicts
4. **Words**: All words must be in TWL dictionary
5. **Tiles**: Must use exactly the tiles in hand

**Cascading Errors**: The system filters downstream errors to show only root causes:
- Parsing errors hide all downstream validation
- Structural errors hide grid conflicts and accidental words
- Errors limited to 5 maximum with actionable tips

## Development

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test suite
uv run pytest tests/test_verify.py -v
uv run pytest tests/test_cascade.py -v

# Run with coverage
uv run pytest tests/ -v --cov=src
```

### Code Quality

```bash
# Run linter
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/
```

## Results

Benchmark results are saved as JSON files containing:
- Full configuration
- Turn-by-turn history with validations
- Complete conversation history for each player
- Final game state and outcome
- Timing information

Example result structure:
```json
{
  "config": {...},
  "winner": "p1",
  "total_turns": 42,
  "end_reason": "Player 1 (gpt-4o) called BANANAS with valid board",
  "player_results": {...},
  "turn_history": [...],
  "conversation_history": {...},
  "duration_seconds": 127.3
}
```

## License

[MIT License][LICENSE]

## Acknowledgements

Thanks to [Michael Fogleman](https://github.com/fogleman) for providing the (Scrabble Tournament Word List)[https://github.com/fogleman/TWL06] verification logic and data.

