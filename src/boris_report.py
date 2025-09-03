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

    # ===== About text (regular styling, below consensus) =====
    ABOUT_BLOCK = """
    <div class="about-block">
      <h3>About</h3>
      <p>Boris is a consensus scanner for selected Nasdaq stocks. It aggregates five independent strategy platforms and flags moments when multiple strategies align in the same direction.</p>
      <p><strong>Grading:</strong>
        <strong>Diamond (5/5)</strong> – all five agree,
        <strong>Strong (4/5)</strong> – four agree,
        <strong>Good (3/5)</strong> – three agree.
        High-grade alignments (4/5 and 5/5) are rare; when they appear, they often coincide with meaningful directional moves. The table is sorted by the strongest signals first.
      </p>

      <h3>Strategy Platforms</h3>
      <ul>
        <li>RSI (Relative Strength Index)</li>
        <li>Keltner Channels</li>
        <li>Supertrend</li>
        <li>Parabolic SAR</li>
        <li>MACD (Moving Average Convergence Divergence)</li>
      </ul>

      <h3>Tickers</h3>
      <p>Current focus: <strong>AAPL, MSFT, NVDA, AMZN, META, TSLA</strong>.<br>
      Coverage will expand to more Nasdaq names.</p>

      <h3>Next to Come</h3>
      <ol>
        <li>Permanent free link to the live report</li>
        <li>Opt-in alerts for Strong and Diamond signals</li>
        <li>Expansion to the full Nasdaq-100 (and beyond)</li>
        <li>Hourly refresh and a simple public feed (JSON/RSS) for integrations</li>
      </ol>
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
    .wrap{max-width:980px;margin:0 auto;padding:24px}
    .header{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
    .brand{display:flex;gap:12px;align-items:center}
    .logo{width:36px;height:36px;border-radius:9px;background:#111827;display:flex;align-items:center;justify-content:center;
          box-shadow:0 6px 18px var(--shadow);font-weight:900;color:var(--accent)}
    .title{font-weight:800;font-size:clamp(20px,3vw,28px)}
    .meta{font-size:12px;color:var(--muted)}
    .muted{color:var(--muted)}
    .spacer{height:10px}
    .card{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:16px;padding:16px;margin-top:18px}
    .highlight{background:rgba(96,165,250,.12);border:1px solid rgba(96,165,250,.35)}
    .consensus-title{margin:0 0 6px 0;font-weight:900;font-size:16px}
    table{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
    th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
    th{font-size:11px;color:#9aa3b2;text-transform:uppercase;letter-spacing:.8px}
    .ticker{font-weight:800}
    .num{text-align:right}
    .badge{padding:4px 8px;border-radius:999px;font-weight:800;font-size:12px;display:inline-block;color:#fff}
    .about-block{margin-top:26px;line-height:1.55}
    .about-block h3{margin:18px 0 8px 0;font-weight:800}
    .about-block p{margin:8px 0}
    .about-block ul, .about-block ol{margin:6px 0 0 18px}
    .footer{margin:24px 0;color:#9aa3b2;font-size:12px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
    @media (max-width:640px){
      .wrap{padding:16px}
      td,th{padding:8px 6px}
      .title{font-size:22px}
    }
    """

    # consensus table (highlighted)
    table = (
        "<div class='card highlight'>"
        "<div class='consensus-title'>Boris Consensus</div>"
        f"<div class='meta'>{summary}</div>"
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
          <div class="title" style="display:flex;align-items:center;justify-content:space-between;">
  <span>Boris Consensus Alerts</span>
  <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://f-j-e.github.io/Boris-Consensus/" 
       alt="QR Code" style="width:60px;height:60px;border-radius:8px;opacity:.9;">
</div>

  <a href="boris_qr.png" title="Scan to open this page">
    <img src="boris_qr.png" alt="QR" style="width:56px;height:56px;border-radius:8px;opacity:.9;">
  </a>
</div>

          <div class="meta">Europe/Zurich · strongest first · {now}</div>
        </div>
      </div>
      <div class="meta">Sorted by strength & votes</div>
    </div>

    {table}

    {ABOUT_BLOCK}

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

# helper retained for completeness
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
