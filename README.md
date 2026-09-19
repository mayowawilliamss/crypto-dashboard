# Crypto Market Health Dashboard

This project monitors the health of the top crypto assets using live market data.

## Business Question

Which major crypto assets are liquid, growing, or showing unusual risk?

## Data Source

Primary source: CoinGecko public API  
Fallback source: Synthetic data generator

## Features

- Live crypto market data collection
- Data quality checks
- Business KPI generation
- Interactive Streamlit dashboard
- Risk flags for unusual price movement

## Key Metrics

- Total market cap
- Total 24h trading volume
- Average 24h price change
- Number of risk-flagged coins
- Top gainer and top loser

## Data Quality Checks

- Row count check
- Required column check
- Duplicate ID check
- Numeric value check
- Positive price check
- Positive market cap check
- Timestamp freshness check
- Extreme price movement warning

## How to Run

```bash
pip install -r requirements.txt
python src/pipeline.py
streamlit run app.py