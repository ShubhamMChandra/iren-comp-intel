# Why: Regenerate README sections from config and scoring weights
# Deps: config, scoring.weights, pathlib
# How: Replace <!-- AUTO: scoring-table --> ... <!-- /AUTO --> with generated table

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import SIGNAL_LABELS, SIGNAL_DESCRIPTIONS
from scoring.weights import SIGNAL_WEIGHTS


def generate_scoring_table() -> str:
    """Build the Scoring Model markdown table from SIGNAL_WEIGHTS and config labels/descriptions."""
    lines = [
        "| Signal | Max Points | What It Detects |",
        "|--------|-----------|-----------------|",
    ]
    for key, cfg in SIGNAL_WEIGHTS.items():
        label = SIGNAL_LABELS.get(key, key.replace("_", " ").title())
        desc = SIGNAL_DESCRIPTIONS.get(key, "")
        lines.append(f"| {label} | {cfg['max_points']} | {desc} |")
    return "\n".join(lines)


def update_readme() -> bool:
    """Replace the scoring-table AUTO block in README.md. Returns True if file was changed."""
    readme_path = ROOT / "README.md"
    content = readme_path.read_text()
    start_marker = "<!-- AUTO: scoring-table -->"
    end_marker = "<!-- /AUTO -->"
    if start_marker not in content or end_marker not in content:
        print("README.md missing <!-- AUTO: scoring-table --> or <!-- /AUTO -->", file=sys.stderr)
        return False
    before = content.split(start_marker)[0]
    after = content.split(end_marker, 1)[1]
    new_content = before + start_marker + "\n" + generate_scoring_table() + "\n" + end_marker + after
    if new_content != content:
        readme_path.write_text(new_content)
        return True
    return False


if __name__ == "__main__":
    changed = update_readme()
    if changed:
        print("README.md updated (scoring table).")
    else:
        print("README.md unchanged.")
