import os, sys, json, datetime as dt
import pandas as pd

OUTDIR = "out"
os.makedirs(OUTDIR, exist_ok=True)

# ===== Sorting: strongest first =====
RANK = {
    "DIAMOND BUY": 300, "DIAMOND SELL": 300,
    "STRONG BUY": 200,  "STRONG SELL": 200,
    "GOOD BUY": 100,    "GOOD SELL": 100,
}

def load_alerts(path="boris_alerts.csv") -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=["date","ticker","consensus","buys","sells"])
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["consensus"] = df["consensus"].astype(str).str.upper()
    for c in ("buys","sells"):
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["rank"] = df["consensus"].map(RANK).fillna(0).astype(int)
    df["margin"] = (df["buys"] - df["sells"]).where(df["consensus"].str.contains("BUY"),
                                                    (df["sells"] - df["buys"]))
    df = df.sort_values(["date","rank","margin","ticker"], ascending=[False,False,False,True]).reset_index(drop=True)
    return df

def summarize(df: pd.DataFrame):
    if df.empty: return "No alerts."
    vc = df["consensus"].value_counts()
    order = ["DIAMOND BUY","DIAMOND SELL","STRONG BUY","STRONG SELL","GOOD BUY","GOOD SELL"]
    parts = [f"{k}: {vc[k]}" for k in order if k in vc]
    return " | ".join(parts) if parts else f"Total alerts: {len(df)}"

def color_for(label: str) -> str:
    l = (label or "").upper()
    if "DIAMOND" in l: return "#7c3aed"
    if "STRONG"  in l: return "#16a34a"
    if "GOOD"    in l: return "#2563eb"
    if "SELL"    in l: return "#b91c1c"
    return "#64748b"

def badge(label: str) -> str:
    return f'<span class="badge" style="background:{color_for(label)}">{(label or "").upper()}</span>'

def to_markdown(df: pd.DataFrame, path_md: str):
    with open(path_md, "w") as f:
        f.write(f"# Boris Consensus Alerts — {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if df.empty: f.write("_No alerts this run._\n"); return
        f.write(summarize(df) + "\n\n")
        f.write("| Date | Ticker | Consensus | Buys | Sells |\n|---|---|---:|---:|---:|\n")
        for _, r in df.iterrows():
            f.write(f"| {r['date'].date()} | {r['ticker']} | {r['consensus']} | {r['buys']} | {r['sells']} |\n")

def to_html(df: pd.DataFrame, path_html: str):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Boris Consensus Alerts — {now}"
    summary = summarize(df)

    # rows
    if df.empty:
        rows_html = "<tr><td colspan='5' class='muted'>No alerts this run.</td></tr>"
    else:
        rows = []
        for _, r in df.iterrows():
            rows.append(
                f"<tr>"
                f"<td>{r['date'].date()}</td>"
                f"<td class='ticker'>{r['ticker']}</td>"
                f"<td>{badge(r['consensus'])}</td>"
                f"<td class='num'>{r['buys']}</td>"
                f"<td class='num'>{r['sells']}</td>"
                f"</tr>"
            )
        rows_html = "\n".join(rows)

    # about content (structured)
    ABOUT_HTML = """
    <div class="card about">
      <div class="section"><div class="section-title">About</div>
        <p>Boris is a consensus scanner for key Nasdaq stocks. It aggregates independent strategy signals to surface rare, higher-conviction moments when methods align.</p>
      </div>
      <div class="grid-2">
        <div class="section">
          <div class="section-title">Strategic Platforms</div>
          <ul class="list">
            <li><b>RSI</b> (Relative Strength Index)</li>
            <li><b>Keltner Channels</b></li>
            <li><b>Supertrend</b></li>
            <li><b>Parabolic SAR</b></li>
            <li><b>MACD</b> (Moving Average Convergence Divergence)</li>
          </ul>
        </div>
        <div class="section">
          <div class="section-title">Tickers</div>
          <p><b>AAPL, MSFT, NVDA, AMZN, META, TSLA</b></p>
          <p class="muted small">Expanding to broader Nasdaq coverage.</p>
        </div>
      </div>
      <div class="section next">
        <div class="section-title">What’s Next</div>
        <div class="next-items">
          <div class="next-item"><b>Permanent free link</b> to the live report.</div>
          <div class="next-item"><b>Alerts</b> for Strong (4/5) & Diamond (5/5) signals.</div>
          <div class="next-item"><b>More tickers</b>: extend to the full Nasdaq-100.</div>
        </div>
      </div>
    </div>
    """

    css = """
    :root{
      --bg:#0b1020;--card:#0f172a;--line:rgba(255,255,255,.08);
      --muted:#9aa3b2;--text:#e5e7eb;--accent:#60a5fa;--shadow:rgba(0,0,0,.35)
    }
    *{box-sizing:border-box}
    body{margin:0;background:linear-gradient(180deg,#0b1020,#0b1123);color:var(--text);
         font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto}
    .wrap{max-width:980px;margin:0 auto;padding:20px}
    .header{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
    .brand{display:flex;gap:10px;align-items:center}
    .logo{width:36px;height:36px;border-radius:9px;background:#111827;display:flex;align-items:center;justify-content:center;
          box-shadow:0 6px 18px var(--shadow);font-weight:900;color:var(--accent)}
    .title{font-weight:800;font-size:clamp(20px,3vw,28px)}
    .meta{font-size:12px;color:var(--muted)}
    .muted{color:var(--muted)}
    .small{font-size:12px}
    .card{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:16px;padding:14px;margin-top:14px}
    .section{margin-top:8px}
    .section-title{font-weight:800;margin:4px 0 8px 0;color:#cbd5e1}
    .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
    .list{margin:.4rem 0 .2rem 1.1rem}
    .highlight{background:rgba(96,165,250,.12);border:1px solid rgba(96,165,250,.35);
               padding:10px 12px;border-radius:12px}
    table{width:100%;border-collapse:collapse;font-size:14px}
    th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
    th{font-size:11px;color:#9aa3b2;text-transform:uppercase;letter-spacing:.8px}
    .ticker{font-weight:800}
    .num{text-align:right}
    .badge{padding:4px 8px;border-radius:999px;font-weight:800;font-size:12px;display:inline-block;color:#fff}
    .footer{margin:16px 0;color:#9aa3b2;font-size:12px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
    .next-items{display:flex;flex-direction:column;gap:8px;margin-top:4px}
    .next-item{padding:8px 10px;border-left:3px solid rgba(96,165,250,.6);background:rgba(255,255,255,.03);border-radius:8px}
    @media (max-width:640px){
      .wrap{padding:14px}
      td,th{padding:8px 6px}
      .title{font-size:22px}
      .grid-2{grid-template-columns:1fr}
    }
    """

    # build table card
    table = (
        "<div class='card'>"
        "<table><thead><tr>"
        "<th>Date</th><th>Ticker</th><th>Consensus</th><th class='num'>Buys</th><th class='num'>Sells</th>"
        "</tr></thead><tbody>"
        + rows_html +
        "</tbody></table></div>"
    )

    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{css}</style>
<body>
  <div class="wrap">
    <div class="header">
      <div class="brand">
        <div class="logo">B</div>
        <div>
          <div class="title">Boris Consensus Alerts</div>
          <div class="meta">Europe/Zurich · strongest first · {now}</div>
        </div>
      </div>
      <div class="meta">Sorted by strength & votes</div>
    </div>

    <div class="card highlight">
      <div class="section-title">Consensus Summary</div>
      <div class="meta">{summary}</div>
    </div>

    {ABOUT_HTML}

    {table}

    <div class="footer">
      <div>Generated by Boris</div>
      <div>Host this HTML on Netlify or GitHub Pages for a public link.</div>
    </div>
  </div>
</body></html>"""
    with open(path_html, "w") as f:
        f.write(html)

def main():
    df = load_alerts()
    print("=== BORIS CONSENSUS SUMMARY ===")
    print(summarize(df))
    if not df.empty:
        print(df[["date","ticker","consensus","buys","sells"]].to_string(index=False))
    print("================================")
    os.makedirs(OUTDIR, exist_ok=True)
    to_markdown(df, os.path.join(OUTDIR, "boris_report.md"))
    to_html(df, os.path.join(OUTDIR, "boris_report.html"))
    with open(os.path.join(OUTDIR, "boris_feed.json"), "w") as f:
        json.dump({"updated": dt.datetime.utcnow().isoformat()+"Z",
                   "alerts": df.to_dict(orient="records")}, f, default=str, indent=2)
    sys.exit(0)

# small helpers (kept for completeness)
def to_markdown(df: pd.DataFrame, path_md: str):
    with open(path_md, "w") as f:
        f.write(f"# Boris Consensus Alerts — {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if df.empty: f.write("_No alerts this run._\n"); return
        f.write(summarize(df) + "\n\n")
        f.write("| Date | Ticker | Consensus | Buys | Sells |\n|---|---|---:|---:|---:|\n")
        for _, r in df.iterrows():
            f.write(f"| {r['date'].date()} | {r['ticker']} | {r['consensus']} | {r['buys']} | {r['sells']} |\n")

if __name__ == "__main__":
    main()
