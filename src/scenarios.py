"""Scenario modelling and valuation logic."""
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ValuationResult:
    """Output of the valuation engine."""
    low_fair_value: float
    base_fair_value: float
    high_fair_value: float
    current_price: float
    flag: str  # "overpay" | "fair" | "underpay"
    margin: float  # % vs base fair value
    max_bid: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "low_fair_value": self.low_fair_value,
            "base_fair_value": self.base_fair_value,
            "high_fair_value": self.high_fair_value,
            "current_price": self.current_price,
            "flag": self.flag,
            "margin_pct": round(self.margin * 100, 1),
            "max_bid": self.max_bid,
        }


@dataclass
class ScenarioTable:
    """Five-scenario breakdown."""
    entry_price: float
    capex_estimate: float
    exit_valuation: float
    gross_profit: float
    roi_pct: float
    annualized_roi_pct: float
    max_bid: float
    hold_period_years: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_price": self.entry_price,
            "capex_estimate": self.capex_estimate,
            "exit_valuation": self.exit_valuation,
            "gross_profit": self.gross_profit,
            "roi_pct": round(self.roi_pct, 1),
            "annualized_roi_pct": round(self.annualized_roi_pct, 1),
            "max_bid": self.max_bid,
            "hold_period_years": self.hold_period_years,
        }


# --- Strategy presets --------------------------------------------------------

STRATEGY_PRESETS = {
    "btl_yield": {
        "name": "Buy-to-Let Yield Play",
        "target_yield_gross": 0.06,      # 6% gross yield target
        "growth_rate_annual": 0.03,      # 3% capital growth
        "capex_pct": 0.02,               # 2% light refresh
        "discount_to_fair": 0.05,        # 5% below fair = max bid
    },
    "refurb_flip": {
        "name": "Refurb & Flip",
        "target_yield_gross": 0.05,
        "growth_rate_annual": 0.04,
        "capex_pct": 0.15,               # 15% heavy refurb
        "discount_to_fair": 0.10,        # 10% below fair = max bid
    },
    "development": {
        "name": "Development / Heavy Value-Add",
        "target_yield_gross": 0.05,
        "growth_rate_annual": 0.05,
        "capex_pct": 0.25,               # 25% major works
        "discount_to_fair": 0.15,
    },
    "hold_long": {
        "name": "Long-Term Hold",
        "target_yield_gross": 0.055,
        "growth_rate_annual": 0.035,
        "capex_pct": 0.03,
        "discount_to_fair": 0.03,
    },
}


def get_preset(strategy_key: str) -> Dict[str, Any]:
    """Return strategy preset or default to btl_yield."""
    key = strategy_key.lower().replace(" ", "_").replace("-", "_")
    # Try exact match, then partial
    if key in STRATEGY_PRESETS:
        return STRATEGY_PRESETS[key]
    for k, v in STRATEGY_PRESETS.items():
        if k in key or key in k:
            return v
    return STRATEGY_PRESETS["btl_yield"]


# --- Valuation engine --------------------------------------------------------

def compute_valuation(
    price: float,
    estimated_rent_annual: Optional[float] = None,
    sqft: Optional[float] = None,
    strategy: str = "btl_yield",
    hold_years: int = 5,
    market_comps: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Compute fair value bands and scenarios.

    If rent is provided: uses yield-based valuation.
    If sqft provided: uses £/sqft comp method.
    Otherwise: uses simple growth-model fallback.
    """
    preset = get_preset(strategy)
    target_yield = preset["target_yield_gross"]
    growth = preset["growth_rate_annual"]
    capex_pct = preset["capex_pct"]
    discount = preset["discount_to_fair"]

    # ---- Fair value estimation ----
    valuations = []

    # Method 1: Yield-based (if rent known)
    if estimated_rent_annual and estimated_rent_annual > 0:
        # Gross yield method: fair = rent / target_yield
        gross_fair = estimated_rent_annual / target_yield
        # Net yield rough adjustment (~25% costs)
        net_fair = (estimated_rent_annual * 0.75) / (target_yield - 0.01)
        valuations.append(gross_fair)
        valuations.append(net_fair)

    # Method 2: £/sqft comp (if sqft known)
    if sqft and sqft > 0:
        # London avg ~£600-900/sqft depending on zone; use conservative £700
        sqft_fair = sqft * 700
        valuations.append(sqft_fair)

    # Method 3: Growth model fallback
    # Future value = price * (1 + growth) ^ hold_years
    # Discount back at 8% target return
    target_return = 0.08
    future_value = price * ((1 + growth) ** hold_years)
    growth_fair = future_value / ((1 + target_return) ** hold_years)
    valuations.append(growth_fair)

    # If we have market comps, add them
    if market_comps:
        valuations.extend(market_comps)

    # ---- Bands ----
    if len(valuations) >= 2:
        valuations.sort()
        base_fair = sum(valuations) / len(valuations)
        low_fair = valuations[0]  # conservative
        high_fair = valuations[-1]  # optimistic
    else:
        base_fair = valuations[0] if valuations else price
        low_fair = base_fair * 0.85
        high_fair = base_fair * 1.15

    # ---- Flag ----
    margin = (price - base_fair) / base_fair if base_fair else 0
    if margin < -0.05:
        flag = "underpay"
    elif margin > 0.05:
        flag = "overpay"
    else:
        flag = "fair"

    max_bid = base_fair * (1 - discount)

    valuation = ValuationResult(
        low_fair_value=round(low_fair, 0),
        base_fair_value=round(base_fair, 0),
        high_fair_value=round(high_fair, 0),
        current_price=price,
        flag=flag,
        margin=abs(margin),
        max_bid=round(max_bid, 0),
    )

    # ---- Scenario table ----
    capex = price * capex_pct
    exit_val = price * ((1 + growth) ** hold_years)
    profit = exit_val - price - capex
    roi = profit / (price + capex) if (price + capex) else 0
    annualized = ((1 + roi) ** (1 / hold_years)) - 1 if hold_years > 0 else 0

    scenario = ScenarioTable(
        entry_price=round(price, 0),
        capex_estimate=round(capex, 0),
        exit_valuation=round(exit_val, 0),
        gross_profit=round(profit, 0),
        roi_pct=roi * 100,
        annualized_roi_pct=annualized * 100,
        max_bid=round(max_bid, 0),
        hold_period_years=hold_years,
    )

    return {
        "valuation": valuation.to_dict(),
        "scenario": scenario.to_dict(),
        "preset_used": preset["name"],
    }


def run_analysis(
    address: str,
    price: float,
    hold_years: int = 5,
    strategy: str = "btl_yield",
    rent_annual: Optional[float] = None,
    sqft: Optional[float] = None,
    extracted_facts: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run full analysis pipeline."""
    result = compute_valuation(
        price=price,
        estimated_rent_annual=rent_annual,
        sqft=sqft,
        strategy=strategy,
        hold_years=hold_years,
    )

    output = {
        "address": address,
        "inputs": {
            "price": price,
            "hold_years": hold_years,
            "strategy": strategy,
            "rent_annual": rent_annual,
            "sqft": sqft,
        },
        "extracted_facts": extracted_facts or {},
        "valuation": result["valuation"],
        "scenario": result["scenario"],
        "strategy_name": result["preset_used"],
    }

    return output


def save_analysis(output: Dict[str, Any], deal_id: str, base_path: str = ".") -> Path:
    """Save analysis to deals/ folder."""
    base = Path(base_path)
    deal_dir = base / "deals" / deal_id
    deal_dir.mkdir(parents=True, exist_ok=True)

    # Save input
    input_path = deal_dir / "input.json"
    with open(input_path, "w") as f:
        json.dump(output["inputs"], f, indent=2)

    # Save extracted facts
    extracted_path = deal_dir / "extracted.json"
    with open(extracted_path, "w") as f:
        json.dump(output["extracted_facts"], f, indent=2)

    # Save full output
    output_path = deal_dir / "output.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return deal_dir
