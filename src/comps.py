"""Comparable analysis (placeholder for v1)."""
from typing import Dict, Any, List, Optional


def simple_comps_table(
    target_price: float,
    target_sqft: Optional[float] = None,
    target_beds: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate a simple comps table.
    In v1 this is a template — v2 will pull live data.
    """
    comps = []

    # Template comp structure
    comp_template = {
        "address": "Comparable Property (manual input needed)",
        "price": target_price,
        "sqft": target_sqft,
        "beds": target_beds,
        "£_per_sqft": round(target_price / target_sqft, 0) if target_sqft else None,
        "source": "User input / PDF extract",
        "date": None,
    }

    comps.append(comp_template)

    return comps


def price_per_sqft(price: float, sqft: float) -> Optional[float]:
    """Calculate £/sqft."""
    if sqft and sqft > 0:
        return round(price / sqft, 0)
    return None
