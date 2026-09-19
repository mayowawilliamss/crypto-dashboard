import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORT_DIR = Path("data/reports")

REQUIRED_COLUMNS = [
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h",
    "last_updated",
]


def ensure_folders():
    for folder in [RAW_DIR, PROCESSED_DIR, REPORT_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def fetch_crypto_markets(limit=50):
    """
    Fetch live crypto market data from CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }

    headers = {
        "accept": "application/json",
        "User-Agent": "beginner-portfolio-project/1.0",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, dict):
        raise ValueError(f"API returned unexpected payload: {payload}")

    return pd.DataFrame(payload)


def generate_fallback_data(limit=50):
    """
    Generate synthetic fallback data if the API fails.
    """
    rng = np.random.default_rng(42)

    base = [
        ("bitcoin", "btc", "Bitcoin"),
        ("ethereum", "eth", "Ethereum"),
        ("tether", "usdt", "Tether"),
        ("binancecoin", "bnb", "BNB"),
        ("solana", "sol", "Solana"),
        ("ripple", "xrp", "XRP"),
        ("usd-coin", "usdc", "USDC"),
        ("cardano", "ada", "Cardano"),
        ("dogecoin", "doge", "Dogecoin"),
        ("avalanche-2", "avax", "Avalanche"),
    ]

    rows = base[:limit]

    while len(rows) < limit:
        i = len(rows)
        rows.append((f"synthetic-coin-{i}", f"syn{i}", f"Synthetic Coin {i}"))

    df = pd.DataFrame(rows, columns=["id", "symbol", "name"])
    n = len(df)

    df["current_price"] = np.round(np.exp(rng.normal(loc=2.0, scale=2.0, size=n)), 6)
    df["circulating_supply"] = rng.integers(1_000_000, 100_000_000, size=n).astype(float)
    df["market_cap"] = np.round(df["current_price"] * df["circulating_supply"], 0)
    df["total_volume"] = np.round(df["market_cap"] * rng.uniform(0.01, 0.35, size=n), 0)
    df["price_change_percentage_24h"] = np.round(rng.normal(0, 6, size=n), 2)
    df["price_change_percentage_7d_in_currency"] = np.round(
        df["price_change_percentage_24h"] + rng.normal(0, 9, size=n), 2
    )
    df["last_updated"] = pd.Timestamp.now(timezone.utc).isoformat()

    df = df.sort_values("market_cap", ascending=False).reset_index(drop=True)
    df["market_cap_rank"] = df.index + 1

    return df


def run_quality_checks(df):
    """
    Run beginner-friendly data quality checks.
    """
    checks = []

    def add(check, status, details):
        checks.append(
            {
                "check": check,
                "status": status,
                "details": details,
            }
        )

    add(
        "row_count",
        "PASS" if len(df) > 0 else "FAIL",
        f"{len(df)} rows returned",
    )

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        add(
            "required_columns",
            "FAIL",
            f"Missing columns: {missing_columns}",
        )
        return pd.DataFrame(checks), df

    add("required_columns", "PASS", "All required columns present")

    duplicate_ids = int(df["id"].duplicated().sum())
    add(
        "no_duplicate_ids",
        "PASS" if duplicate_ids == 0 else "FAIL",
        f"{duplicate_ids} duplicate ids",
    )

    numeric_columns = [
        "current_price",
        "market_cap",
        "total_volume",
        "price_change_percentage_24h",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    missing_numeric = int(df[numeric_columns].isna().sum().sum())
    add(
        "numeric_values_present",
        "PASS" if missing_numeric == 0 else "WARN",
        f"{missing_numeric} missing numeric values",
    )

    bad_price = int((df["current_price"] <= 0).sum())
    add(
        "price_positive",
        "PASS" if bad_price == 0 else "FAIL",
        f"{bad_price} non-positive prices",
    )

    bad_market_cap = int((df["market_cap"] <= 0).sum())
    add(
        "market_cap_positive",
        "PASS" if bad_market_cap == 0 else "FAIL",
        f"{bad_market_cap} non-positive market caps",
    )

    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce", utc=True)

    missing_timestamps = int(df["last_updated"].isna().sum())
    add(
        "timestamp_present",
        "PASS" if missing_timestamps == 0 else "WARN",
        f"{missing_timestamps} missing timestamps",
    )

    if df["last_updated"].notna().any():
        newest = df["last_updated"].max()
        age_hours = (pd.Timestamp.now(timezone.utc) - newest).total_seconds() / 3600

        if age_hours <= 24:
            status = "PASS"
        elif age_hours <= 72:
            status = "WARN"
        else:
            status = "FAIL"

        add(
            "data_freshness",
            status,
            f"Newest record is {age_hours:.1f} hours old",
        )
    else:
        add(
            "data_freshness",
            "FAIL",
            "No valid timestamps found",
        )

    extreme_moves = int(df["price_change_percentage_24h"].abs().gt(50).sum())
    add(
        "extreme_24h_move_review",
        "PASS" if extreme_moves == 0 else "WARN",
        f"{extreme_moves} coins moved more than 50% in 24h",
    )

    return pd.DataFrame(checks), df


def build_kpis(df, source_name):
    """
    Build business KPIs from the cleaned data.
    """
    df = df.copy()

    df["volume_to_market_cap"] = df["total_volume"] / df["market_cap"].replace(0, pd.NA)
    df["risk_flag"] = df["price_change_percentage_24h"].abs().ge(10)

    top_gainer = ""
    top_loser = ""

    if df["price_change_percentage_24h"].notna().any():
        top_gainer = df.loc[df["price_change_percentage_24h"].idxmax(), "name"]
        top_loser = df.loc[df["price_change_percentage_24h"].idxmin(), "name"]

    kpis = {
        "snapshot_time": pd.Timestamp.now(timezone.utc),
        "source": source_name,
        "number_of_coins": int(len(df)),
        "total_market_cap_usd": float(df["market_cap"].sum()),
        "total_volume_usd": float(df["total_volume"].sum()),
        "average_24h_change_pct": float(df["price_change_percentage_24h"].mean()),
        "median_24h_change_pct": float(df["price_change_percentage_24h"].median()),
        "coins_up_24h": int((df["price_change_percentage_24h"] > 0).sum()),
        "coins_down_24h": int((df["price_change_percentage_24h"] < 0).sum()),
        "risk_flag_count": int(df["risk_flag"].sum()),
        "top_gainer": top_gainer,
        "top_loser": top_loser,
    }

    return kpis, df


def save_outputs(df, report, kpis):
    """
    Save raw, processed, KPI, and quality report files.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    raw_path = RAW_DIR / f"crypto_markets_raw_{ts}.csv"
    df.to_csv(raw_path, index=False)
    df.to_csv(RAW_DIR / "latest_raw.csv", index=False)

    markets_path = PROCESSED_DIR / "latest_markets.csv"
    df.to_csv(markets_path, index=False)
    df.to_csv(PROCESSED_DIR / f"markets_{ts}.csv", index=False)

    kpi_df = pd.DataFrame([kpis])
    kpi_df.to_csv(PROCESSED_DIR / "latest_kpis.csv", index=False)
    kpi_df.to_csv(PROCESSED_DIR / f"kpis_{ts}.csv", index=False)

    report.to_csv(REPORT_DIR / "latest_quality_report.csv", index=False)
    report.to_csv(REPORT_DIR / f"quality_report_{ts}.csv", index=False)

    print(f"Saved raw data to {raw_path}")
    print(f"Saved processed market data to {markets_path}")
    print(f"Saved KPIs to {PROCESSED_DIR / 'latest_kpis.csv'}")
    print(f"Saved quality report to {REPORT_DIR / 'latest_quality_report.csv'}")


def run_pipeline(use_fallback=False, limit=50):
    ensure_folders()

    source_name = "coingecko_api"

    if use_fallback:
        print("Using fallback synthetic data.")
        df = generate_fallback_data(limit)
        source_name = "fallback_synthetic"
    else:
        try:
            print("Fetching data from CoinGecko...")
            df = fetch_crypto_markets(limit)
        except Exception as exc:
            print(f"API fetch failed: {exc}")
            print("Falling back to synthetic data.")
            df = generate_fallback_data(limit)
            source_name = "fallback_synthetic"

    report, df = run_quality_checks(df)
    kpis, df = build_kpis(df, source_name)
    save_outputs(df, report, kpis)

    failed_checks = report[report["status"] == "FAIL"]

    if not failed_checks.empty:
        print("\nWARNING: Some quality checks failed:")
        print(failed_checks)
    else:
        print("\nAll hard quality checks passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and validate crypto market data."
    )

    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Use synthetic data instead of live API",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of coins to fetch",
    )

    args = parser.parse_args()

    run_pipeline(use_fallback=args.fallback, limit=args.limit)