# Real Estate Deal Analyzer

A personal deal analysis tool for property investment due diligence.

## Stack
- Python + Streamlit for UI
- Local JSON/CSV storage (no database)
- Jupyter notebook for prototyping

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
│   ├── comps.py           # Comparable analysis
│   ├── scenarios.py       # Scenario modelling
│   ├── memo.py            # Memo generation
│   └── utils.py           # Helpers
└── deals/                 # Individual deal folders
    └── deal_001/
        ├── input.json
        ├── memo.pdf
        ├── extracted.json
        └── output.md
```

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the notebook (prototype):
```bash
jupyter notebook deal_analyzer_v1.ipynb
```

3. Run the Streamlit app:
```bash
streamlit run app.py
```

## v1 Scope
- Upload a property memo PDF
- Enter address, price, hold period, strategy
- Get: extracted facts, fair value band, scenario table, markdown memo
