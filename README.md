# Real Estate Deal Analyzer

A personal deal analysis tool for property investment due diligence.

**Now with live market data:** Real sold prices from HM Land Registry + active rental comps from Rightmove.

## What's New (v1.1)

- **🔴 Live Market Data** — No more guessing £/sqft. Uses actual sold prices
- **🏘️ Rental Comps** — Gross yield calculated from live Rightmove listings
- **📊 Auto Fair Value** — Based on comparable sales, not thumb-suck numbers

## Stack
- Python + Streamlit for UI
- HM Land Registry API (free, no key)
- Rightmove internal API (scraped)
- Local JSON/CSV storage

## Quick Start

```bash
cd real_estate_dd
source venv/bin/activate  # if using venv
streamlit run app.py
```

## Using Live Data

1. Enter a UK postcode in the sidebar
2. Check "Use Live Market Data"
3. Click **Analyze**
4. The app fetches:
   - Recent sold prices (Land Registry, last 2 years)
   - Active rental listings (Rightmove, same area)
   - Calculates real fair value and yield

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| HM Land Registry | Sold prices (1995-present) | Free |
| Rightmove | Active rental/sales listings | Free (scraped) |

## Folder Structure

```
real_estate_dd/
├── app.py                  # Streamlit interface
├── requirements.txt
├── README.md
├── data/
│   ├── raw/               # Uploaded PDFs, raw inputs
│   ├── processed/         # Extracted text, normalized data
│   └── outputs/           # Generated memos, reports
├── docs/
│   ├── prompt_notes.md    # System prompts & instructions
│   └── valuation_logic.md # Valuation framework docs
├── src/
│   ├── extract.py         # PDF text extraction
│   ├── normalize.py       # Data normalization
│   ├── scenarios.py       # Scenario modelling
│   ├── memo.py            # Memo generation
│   ├── utils.py           # Helpers
│   ├── land_registry.py   # HM Land Registry API client
│   ├── rightmove_scraper.py # Rightmove rental/sales scraper
│   └── live_data.py       # Unified live data fetcher
└── deals/                 # Individual deal folders
    └── deal_001/
        ├── input.json
        ├── extracted.json
        └── output.md
```

## Example Output

```
📊 Live Market Data for SW1A 1AA

🏠 Sold Prices (last 2 years):
   15 sales | Avg: £1,245,000 | Median: £1,180,000
   Range: £895,000 - £1,650,000

🏘️ Rental Comps (active listings):
   8 properties | Avg: £4,200/mo
   Range: £3,500 - £5,000/mo

📈 Estimated Gross Yield: 4.05%
📐 Est. £/sqft: £1,142
```

## Valuation Methods

When live data is enabled:

1. **Recent Sales Average** — Mean of Land Registry sold prices
2. **Yield-Based** — Annual rent / target yield (5.5%)
3. **£/sqft Method** — If sqft data available from rentals

Fair value = average of available methods. Asking price compared to this.

## v1 Scope
- Upload a property memo PDF
- Enter address, price, hold period, strategy
- Get: extracted facts, fair value band, scenario table, markdown memo

## v1.1 Live Data
- Automatic postcode-based comp lookup
- Real sold price history
- Active rental market data
- Gross yield estimation
