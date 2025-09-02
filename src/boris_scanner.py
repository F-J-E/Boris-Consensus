from __future__ import annotations
import os, sys, logging, time, random, io
import requests
import pandas as pd
import yfinance as yf

from src.utils import load_cfg, setup_logger, now_str, ensure_dir
from src.indicators import add_indicators
from src.consensus import indicator_signals, consensus_from_signals

def load_tickers(path: str) -> list[str]:
    with open(path, "r") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip() and not ln.strip().startswith("#")]
    seen, out = set(), []
    for t in lines:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def fetch_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    Fetch historical daily candles from Stooq (no API key).
    US stocks require the '.us' suffix, e.g., aapl.us
    """
    import requests, io, re

    # Build stooq symbol
    base = ticker.strip().lower()
    # If it doesn't already have a suffix (like .us, .de, .pl), default to .us
    if not re.search(r"\.[a-z]{2,3}$", base):
        base = f"{base}.us"

    url = f"https://stooq.com/q/d/l/?s={base}&i=d"
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    text = r.text.strip()

    # Validate CSV header
    first_line = text.splitlines()[0] if text else ""
    if not first_line.lower().startswith("date,"):
        preview = text[:120].replace("\n", "\\n")
        raise RuntimeError(f"Stooq returned non-CSV for {base}: '{preview}'")

    df = pd.read_csv(io.StringIO(text), parse_dates=["Date"])
    if df.empty:
        raise RuntimeError(f"No data for {ticker} via Stooq")

    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }).sort_values("date").reset_index(drop=True)

    # Trim by period like '365d'
    days = 365
    try:
        if str(period).endswith("d"):
            days = int(str(period)[:-1])
    except Exception:
        pass
    if len(df) > days:
        df = df.iloc[-days:].reset_index(drop=True)

    if interval != "1d":
        raise RuntimeError("Stooq supports only daily (1d) interval")

    return df


    # --- Primary: Yahoo with retries ---
    for i in range(attempts):
        try:
            df = yf.download(
                tickers=ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.reset_index().rename(columns={df.columns[0]: "date"})
                return df

            # Secondary within Yahoo
            hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            if isinstance(hist, pd.DataFrame) and not hist.empty:
                hist = hist.reset_index().rename(columns={hist.columns[0]: "date"})
                return hist

            last_err = RuntimeError(f"No data from Yahoo for {ticker}")
        except Exception as e:
            last_err = e

        time.sleep(1.0 + i * 1.5 + random.random() * 0.5)

    # --- Fallback: Stooq CSV (daily only) ---
    try:
        stq_symbol = f"{ticker.lower()}.us"   # e.g., aapl.us
        url = f"https://stooq.com/q/d/l/?s={stq_symbol}&i=d"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        text = r.text.strip()
        if text and text.splitlines()[0].lower().startswith("date,"):
            csv_df = pd.read_csv(io.StringIO(text))
            if not csv_df.empty:
                csv_df = csv_df.rename(columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                })
                csv_df["date"] = pd.to_datetime(csv_df["date"])
                csv_df = csv_df.sort_values("date").reset_index(drop=True)

                # Trim to requested days from '365d' etc.
                days = 365
                try:
                    if period.endswith("d"):
                        days = int(period[:-1])
                except Exception:
                    pass
                if len(csv_df) > days:
                    csv_df = csv_df.iloc[-days:].reset_index(drop=True)

                if interval != "1d":
                    raise RuntimeError("Stooq fallback supports only daily interval")
                return csv_df

        raise RuntimeError(f"No data from Stooq for {ticker}")
    except Exception as e:
        raise RuntimeError(f"No data for {ticker}") from (e if e else last_err)


def scan_ticker(ticker: str, cfg: dict) -> dict | None:
    try:
        df = fetch_history(ticker, cfg["period"], cfg["interval"])
        if len(df) < cfg.get("min_rows", 200):
            logging.warning(f"{ticker}: insufficient rows {len(df)} < {cfg.get('min_rows',200)}")
            return None
        df = add_indicators(df, cfg)
        last = df.iloc[-1]
        sigs = indicator_signals(last, cfg)
        label, buys, sells = consensus_from_signals(sigs, cfg)
        return {
            "ticker": ticker,
            "timestamp": last["date"].strftime("%Y-%m-%d"),
            "close": round(float(last["close"]), 4),
            "buys": buys,
            "sells": sells,
            "consensus": label,
        }
    except Exception as e:
        logging.exception(f"{ticker}: scan failed: {e}")
        return None


def export_csv(rows: list[dict], path: str):
    # Alerts-only, consensus-focused output
    cols = ["date","ticker","consensus","buys","sells"]
    tidy = []
    for r in rows:
        tidy.append({
            "date": r.get("timestamp"),
            "ticker": r.get("ticker"),
            "consensus": r.get("consensus"),
            "buys": r.get("buys", 0),
            "sells": r.get("sells", 0),
        })
    pd.DataFrame(tidy, columns=cols).to_csv(path, index=False)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = load_cfg(os.path.join(root, "config.yaml"))
    setup_logger(cfg.get("log_level", "INFO"))

    tzname = cfg.get("timezone", "Europe/Zurich")
    logging.info(f"Starting Boris daily scan @ {now_str(tzname)}")

    tickers = load_tickers(os.path.join(root, "tickers.csv"))
    logging.info(f"Tickers: {len(tickers)}")

    results = []
    for t in tickers:
        r = scan_ticker(t, cfg)
        if r:
            results.append(r)
        time.sleep(0.8)

    outdir = cfg.get("output_dir", ".")
    ensure_dir(outdir)

    # consensus threshold
    def tier_score(label: str) -> int:
        l = (label or "").upper()
        if "DIAMOND" in l: return 3
        if "STRONG"  in l: return 2
        if "GOOD"    in l: return 1
        return 0

    tier = cfg.get("alerts_min_consensus", "strong").lower()
    min_needed = {"good":1, "strong":2, "diamond":3}.get(tier, 2)

    alerts = [r for r in results if tier_score(r.get("consensus","")) >= min_needed]

    alerts_path = os.path.join(outdir, "boris_alerts.csv")
    export_csv(alerts, alerts_path)
    logging.info(f"ALERTS: wrote {alerts_path} ({len(alerts)} rows)")

    if alerts:
        logging.info("==== CONSENSUS ALERTS ====")
        for r in alerts:
            logging.info(f"{r['timestamp']} | {r['ticker']} | {r['consensus']} (buys={r['buys']}, sells={r['sells']})")
        logging.info("==== ================== ====")
    else:
        logging.info("No consensus alerts this run.")

    exit_code = 0
    if any("DIAMOND" in (r.get("consensus","")) for r in alerts):
        exit_code = 2
    elif any("STRONG" in (r.get("consensus","")) for r in alerts):
        exit_code = 1

    logging.info(f"Done. Exit code hint = {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

