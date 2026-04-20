"""Utility helpers."""
import json
import re
from pathlib import Path
from typing import Dict, Any


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '_', text)
    return text[:50]


def format_currency(value: float) -> str:
    """Format as GBP currency string."""
    return f"£{value:,.0f}"


def format_pct(value: float) -> str:
    """Format as percentage."""
    return f"{value:.1f}%"


def safe_json_load(path: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def safe_json_save(data: Dict[str, Any], path: Path) -> None:
    """Save JSON file safely."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
