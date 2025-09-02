from __future__ import annotations
import pandas as pd
import pandas_ta as ta

def add_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    # Ensure standard OHLCV columns exist
    cols = {c.lower(): c for c in df.columns}
    rename = {}
    for need in ["open", "high", "low", "close", "volume"]:
        if need not in cols:
            raise ValueError(f"Missing column: {need}")
        rename[cols[need]] = need
    df = df.rename(columns=rename)

    # Keltner Channels
    kc = ta.kc(high=df["high"], low=df["low"], close=df["close"],
               length=cfg["keltner"]["length"],
               scalar=cfg["keltner"]["mult"])
    df = pd.concat([df, kc], axis=1)

    # Supertrend
    st = ta.supertrend(high=df["high"], low=df["low"], close=df["close"],
                       length=cfg["supertrend"]["length"],
                       multiplier=cfg["supertrend"]["multiplier"])
    df = pd.concat([df, st], axis=1)

    # RSI
    rsi = ta.rsi(df["close"], length=cfg["rsi"]["length"])
    df["RSI"] = rsi

    # Parabolic SAR
    psar = ta.psar(high=df["high"], low=df["low"], close=df["close"],
                   af=cfg["psar"]["af"], max_af=cfg["psar"]["max_af"])
    df = pd.concat([df, psar], axis=1)

    # MACD
    macd = ta.macd(df["close"],
                   fast=cfg["macd"]["fast"], slow=cfg["macd"]["slow"], signal=cfg["macd"]["signal"])
    df = pd.concat([df, macd], axis=1)

    return df
