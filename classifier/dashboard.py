import os
import html
from datetime import datetime, timezone

from drift_history import get_recent_events, get_summary

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")


def _row_html(event):
    timestamp, resource, field, classification, reason, action, pr_url = event

    is_safe = classification == "SAFE"
    badge_color = "#4ade9a" if is_safe else "#ef7a5f"
    badge_bg = "rgba(74,222,154,0.12)" if is_safe else "rgba(239,122,95,0.14)"

    display_time = html.escape(timestamp[:16].replace("T", " "))
    pr_cell = f'<a href="{html.escape(pr_url)}">view &rarr;</a>' if pr_url else '<span style="color:#4a5157;">&mdash;</span>'

    return f"""
        <tr>
          <td style="color: #7d8790;">{display_time}</td>
          <td>{html.escape(resource)}</td>
          <td style="color: #b7bfc6;">{html.escape(field)}</td>
          <td><span style="background: {badge_bg}; color: {badge_color}; border-radius: 3px; padding: 2px 8px; font-size: 12px;">{html.escape(classification)}</span></td>
          <td style="color: #b7bfc6;">{html.escape(action)}</td>
          <td>{pr_cell}</td>
        </tr>"""


def render_dashboard():
    summary = get_summary()
    events = get_recent_events()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if events:
        rows_html = "".join(_row_html(e) for e in events)
    else:
        rows_html = """
        <tr><td colspan="6" style="text-align:center; color:#7d8790; padding: 48px 0;">No drift detected yet. TerraGuard checks every 6 hours.</td></tr>"""

    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TerraGuard &mdash; Drift History</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap">
<style>
  :root{{
    --bg:#111417; --panel:#181c20; --border:#2a3036;
    --text:#e7ebee; --muted:#7d8790;
    --safe:#4ade9a; --risky:#ef7a5f; --neutral:#8fa8c9;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  a {{ color: var(--neutral); text-decoration: none; }}
  a:hover {{ color: var(--text); text-decoration: underline; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th {{ text-align: left; font-weight: 500; letter-spacing: 0.06em; font-size: 11px; color: var(--muted); text-transform: uppercase; padding: 16px 14px 10px 14px; }}
  td {{ padding: 12px 14px; font-size: 13px; border-top: 1px solid var(--border); }}
  tr:hover td {{ background: #1c2126; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 40px 32px; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .stat {{ flex: 1; min-width: 140px; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 18px 20px; }}
  .stat-label {{ font-size: 11px; letter-spacing: 0.06em; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; }}
  .stat-value {{ font-size: 30px; font-weight: 600; }}
  .table-scroll {{ overflow-x: auto; }}
</style>
</head>
<body>
<div class="wrap">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; flex-wrap: wrap; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 12px;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4ade9a" stroke-width="1.6">
        <path d="M12 2 L21 6 V12 C21 17 17 20.5 12 22 C7 20.5 3 17 3 12 V6 Z" />
        <path d="M8.5 12.2 L11 14.7 L15.5 9.7" />
      </svg>
      <div style="font-size: 18px; font-weight: 600;">TerraGuard</div>
      <div style="font-size: 11px; color: var(--muted); border: 1px solid var(--border); border-radius: 3px; padding: 2px 7px;">DRIFT HISTORY</div>
    </div>
    <div style="font-size: 12px; color: var(--muted);">last updated {generated_at} &middot; refreshes every 6h</div>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-label">total events</div>
      <div class="stat-value">{summary['total']}</div>
    </div>
    <div class="stat">
      <div class="stat-label">safe</div>
      <div class="stat-value" style="color: var(--safe);">{summary['safe']}</div>
    </div>
    <div class="stat">
      <div class="stat-label">risky</div>
      <div class="stat-value" style="color: var(--risky);">{summary['risky']}</div>
    </div>
    <div class="stat">
      <div class="stat-label">auto-fixed</div>
      <div class="stat-value" style="color: var(--neutral);">{summary['auto_fixed']}</div>
    </div>
  </div>

  <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 6px;" class="table-scroll">
    <table>
      <thead>
        <tr><th>time</th><th>resource</th><th>field</th><th>class</th><th>action</th><th>pr</th></tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>

  <div style="margin-top: 14px; font-size: 11px; color: #4a5157;">generated automatically by drift-check.yml on every scheduled run</div>
</div>
</body>
</html>
"""

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"Dashboard written to {OUTPUT_PATH}")


if __name__ == "__main__":
    render_dashboard()
