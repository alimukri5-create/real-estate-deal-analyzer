# Valuation Logic Documentation

## v1 Fair Value Methods

### Method 1: Gross Yield
```
Fair Value = Annual Rent / Target Gross Yield
```
Target yields by strategy:
- BTL Yield Play: 6%
- Refurb & Flip: 5%
- Development: 5%
- Long-Term Hold: 5.5%

### Method 2: £/sqft Comps
```
Fair Value = sqft × £700 (London baseline, conservative)
```
v2 will use live comp data.

### Method 3: Growth Model
```
Future Value = Price × (1 + growth_rate) ^ hold_years
Fair Value = Future Value / (1 + target_return) ^ hold_years
```
- Target return: 8%
- Growth rate varies by strategy (3-5%)

## Scenario Math

```
Capex = Price × capex_pct
Exit = Price × (1 + growth) ^ hold_years
Profit = Exit - Price - Capex
ROI = Profit / (Price + Capex)
Annualized ROI = (1 + ROI) ^ (1 / hold_years) - 1
Max Bid = Base Fair × (1 - discount_to_fair)
```

## Strategy Presets

| Strategy | Target Yield | Growth | Capex % | Discount |
|----------|-------------|--------|---------|----------|
| BTL Yield | 6% | 3% | 2% | 5% |
| Refurb Flip | 5% | 4% | 15% | 10% |
| Development | 5% | 5% | 25% | 15% |
| Long-Term Hold | 5.5% | 3.5% | 3% | 3% |

## Flag Rules
- Underpay: Price < 95% of base fair
- Fair: Price within ±5% of base fair
- Overpay: Price > 105% of base fair
