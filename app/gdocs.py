"""
gdocs.py — HTML Student Page Generator
========================================
Creates one beautifully formatted HTML page per student.
Pages are saved to /student_pages/ folder locally.
FastAPI serves them at /pages/ — accessible via ngrok URL.

No Google APIs needed. Zero quota issues.
"""

import os
import re
from datetime import datetime
from pathlib import Path

TEACHER_NAME = os.getenv("TEACHER_NAME", "Ms. Priya")
PAGES_DIR = Path("student_pages")


def _slug(name: str) -> str:
    """Convert 'Ananya Sharma' → 'ananya-sharma' for filename."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def create_student_doc(student_data: dict) -> str:
    """
    Generate a formatted HTML student page and save it locally.
    Returns the public ngrok-accessible URL.
    """
    PAGES_DIR.mkdir(exist_ok=True)

    student_name = student_data.get("student_name", "Unknown Student")
    course_level = student_data.get("course_level", "Not specified")
    instrument   = student_data.get("instrument", "Not specified")
    month        = student_data.get("month", datetime.now().strftime("%B %Y"))
    summary      = student_data.get("feedback_summary", "")
    actions      = student_data.get("action_points", [])
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")

    action_items = "\n".join(f"<li>{ap}</li>" for ap in actions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{student_name} – Feedback ({month})</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', sans-serif; background:#f4f1eb; color:#1a1a1a; line-height:1.6; }}
  .header {{ background:#1a1a1a; color:#fff; padding:40px; }}
  .header .tag {{
    background:#c94f2b; color:#fff; font-size:11px; font-weight:700;
    letter-spacing:2px; text-transform:uppercase; padding:4px 12px;
    border-radius:3px; display:inline-block; margin-bottom:16px;
  }}
  .header h1 {{ font-size:36px; font-weight:800; margin-bottom:6px; }}
  .header .sub {{ color:#aaa; font-size:15px; }}
  .meta {{
    display:flex; gap:32px; flex-wrap:wrap;
    padding:24px 40px; background:#fff;
    border-bottom:2px solid #e0dbd0; font-size:14px;
  }}
  .meta-item strong {{
    display:block; font-size:11px; color:#888;
    text-transform:uppercase; letter-spacing:1px; margin-bottom:3px;
  }}
  .body {{ max-width:800px; margin:32px auto; padding:0 24px 60px; }}
  .card {{
    background:#fff; border-radius:10px; padding:32px;
    margin-bottom:24px; border:1px solid #e0dbd0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }}
  .card h2 {{
    font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:2px; margin-bottom:16px; padding-bottom:10px;
    border-bottom:1px solid #f0ece4;
  }}
  .card.feedback h2 {{ color:#c94f2b; }}
  .card.actions h2 {{ color:#2b6cc9; }}
  .card p {{ font-size:15px; line-height:1.8; color:#333; }}
  .card ol {{ padding-left:20px; }}
  .card ol li {{
    font-size:15px; line-height:1.8; color:#333;
    margin-bottom:10px; padding-left:4px;
  }}
  .footer {{
    text-align:center; font-size:12px; color:#aaa;
    padding:24px; border-top:1px solid #e0dbd0;
    margin-top:20px;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="tag">Udukku Music · Student Feedback</div>
  <h1>{student_name}</h1>
  <div class="sub">{course_level} &nbsp;·&nbsp; {instrument}</div>
</div>

<div class="meta">
  <div class="meta-item"><strong>Month</strong>{month}</div>
  <div class="meta-item"><strong>Course Level</strong>{course_level}</div>
  <div class="meta-item"><strong>Instrument</strong>{instrument}</div>
  <div class="meta-item"><strong>Teacher</strong>{TEACHER_NAME}</div>
  <div class="meta-item"><strong>Generated</strong>Auto · AI Pipeline</div>
</div>

<div class="body">

  <div class="card feedback">
    <h2>📊 This Month's Feedback</h2>
    <p>{summary}</p>
  </div>

  <div class="card actions">
    <h2>🎯 Action Points for Next Month</h2>
    <ol>
      {action_items}
    </ol>
  </div>

</div>

<div class="footer">
  Generated automatically on {generated_at} &nbsp;·&nbsp;
  Powered by Whisper + LLaMA + Udukku Music Feedback Bot
</div>

</body>
</html>"""

    # ── Save file ────────────────────────────────────────────────────────────
    filename = f"{_slug(student_name)}-{datetime.now().strftime('%Y%m')}.html"
    filepath = PAGES_DIR / filename
    filepath.write_text(html, encoding="utf-8")
    print(f"✅ Student page saved: {filepath}")

    # ── Build public URL ─────────────────────────────────────────────────────
    base_url = os.getenv("NGROK_URL", "http://localhost:5678").rstrip("/")
    page_url = f"{base_url}/pages/{filename}"
    return page_url