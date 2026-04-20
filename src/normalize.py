"""Data normalization helpers."""
import re
from typing import Optional


def normalize_price(value) -> Optional[float]:
    """Extract numeric price from string or number."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove £, commas, spaces
        cleaned = re.sub(r'[£,\s]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def normalize_rent(value) -> Optional[float]:
    """Extract monthly or annual rent."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r'[£,\s]', '', value)
        # Detect annual vs monthly
        if 'pa' in value.lower() or 'annual' in value.lower():
            try:
                return float(cleaned)
            except ValueError:
                return None
        else:
            # Assume monthly, convert to annual
            try:
                return float(cleaned) * 12
            except ValueError:
                return None
    return None


def normalize_address(value: str) -> str:
    """Clean and standardize address."""
    if not value:
        return ""
    # Basic cleanup
    addr = value.strip()
    addr = re.sub(r'\s+', ' ', addr)
    return addr
