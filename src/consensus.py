from __future__ import annotations
import pandas as pd

def indicator_signals(row: pd.Series, cfg: dict) -> dict:
    sig = {}

    # Keltner: close above upper => BUY, below lower => SELL
    upper = row.get("KCU_20_2.0") or row.get("KCU_20_2")
    lower = row.get("KCL_20_2.0") or row.get("KCL_20_2")
    close = row["close"]
    if upper is not None and lower is not None:
        if close > upper:
            sig["keltner"] = "BUY"
        elif close < lower:
            sig["keltner"] = "SELL"
        else:
            sig["keltner"] = "NEUTRAL"

    # Supertrend direction
    st_dir = None
    for key in row.index:
        if str(key).startswith("SUPERTd_"):
            st_dir = row[key]
            break
    if st_dir is not None:
        sig["supertrend"] = "BUY" if st_dir == 1 else "SELL"

    # RSI thresholds
    rsi = row.get("RSI")
    if pd.notna(rsi):
        if rsi >= cfg["rsi"]["buy"]:
            sig["rsi"] = "BUY"
        elif rsi <= cfg["rsi"]["sell"]:
            sig["rsi"] = "SELL"
        else:
            sig["rsi"] = "NEUTRAL"

    # PSAR: close above psar => BUY else SELL
    psar = None
    for key in row.index:
        if str(key).startswith("PSARr_"):
            psar = row[key]
            break
    if psar is not None:
        sig["psar"] = "BUY" if close > psar else "SELL"

    # MACD: macd above signal => BUY, below => SELL
    macd = row.get("MACD_12_26_9")
    macds = row.get("MACDs_12_26_9")
    if pd.notna(macd) and pd.notna(macds):
        sig["macd"] = "BUY" if macd > macds else "SELL"

    return sig

def consensus_from_signals(sig: dict, cfg: dict) -> tuple[str, int, int]:
    buys = sum(1 for v in sig.values() if v == "BUY")
    sells = sum(1 for v in sig.values() if v == "SELL")

    label = "NONE"
    if buys >= cfg["consensus"]["diamond"]:
        label = "DIAMOND BUY"
    elif buys >= cfg["consensus"]["strong"]:
        label = "STRONG BUY"
    elif buys >= cfg["consensus"]["good"]:
        label = "GOOD BUY"
    elif sells >= cfg["consensus"]["diamond"]:
        label = "DIAMOND SELL"
    elif sells >= cfg["consensus"]["strong"]:
        label = "STRONG SELL"
    elif sells >= cfg["consensus"]["good"]:
        label = "GOOD SELL"

    return label, buys, sells
