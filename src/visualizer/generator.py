"""Generate self-contained HTML visualizer from game results."""

import json
from pathlib import Path
from typing import Optional


def generate_visualizer(
    results_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> Path:
    """
    Generate a self-contained HTML visualizer from game results.

    Args:
        results_path: Path to the results JSON file
        output_path: Output path for HTML (defaults to same name with .html)

    Returns:
        Path to the generated HTML file
    """
    results_path = Path(results_path)

    if output_path is None:
        output_path = results_path.with_suffix(".html")
    else:
        output_path = Path(output_path)

    # Load game data
    with open(results_path) as f:
        game_data = json.load(f)

    # Load template and assets
    module_dir = Path(__file__).parent
    template_path = module_dir / "templates" / "visualizer.html"
    css_path = module_dir / "assets" / "styles.css"
    js_path = module_dir / "assets" / "app.js"

    with open(template_path) as f:
        template = f.read()

    with open(css_path) as f:
        css = f.read()

    with open(js_path) as f:
        js = f.read()

    # Build game title from player names
    players = game_data.get("config", {}).get("players", [])
    player_names = [p.get("name", p.get("model", "Unknown")) for p in players]
    if len(player_names) == 0:
        game_title = "Banana-Bench Game"
    elif len(player_names) == 1:
        game_title = player_names[0]
    elif len(player_names) == 2:
        game_title = f"{player_names[0]} vs {player_names[1]}"
    else:
        game_title = f"{player_names[0]} vs {player_names[1]} + {len(player_names) - 2} more"

    # Substitute template variables
    html = template.replace("{{ inline_css }}", css)
    html = html.replace("{{ inline_js }}", js)
    html = html.replace("{{ game_data_json }}", json.dumps(game_data))
    html = html.replace("{{ game_title }}", game_title)
    html = html.replace("{{ total_turns }}", str(game_data.get("total_turns", 0)))
    html = html.replace("{{ end_reason }}", game_data.get("end_reason", ""))
    html = html.replace("{{ num_players }}", str(len(players)))

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path
