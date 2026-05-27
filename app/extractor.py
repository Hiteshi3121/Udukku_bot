"""
extractor.py — Prompt Engineering Core
=======================================
Two-stage prompting:
  Stage 1: Cleanup raw Whisper transcript (remove fillers, fix grammar)
  Stage 2: Extract structured student data as JSON

Changes:
  - Student name always extracted from transcript (no caption needed)
  - Missing fields default to "Not specified" — never null, never crash
  - Existing student_data can be passed in to preserve previous values
"""

import json
import re
from groq import Groq
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT 1 — Transcription Cleanup
# ─────────────────────────────────────────────────────────────────────────────
CLEANUP_SYSTEM_PROMPT = """You are a transcription editor for a music school called Udukku Music.
You receive raw voice note transcripts from a teacher and clean them up.

Your rules:
- Remove all filler words: um, uh, like, you know, basically, actually, right, okay so
- Fix grammar and punctuation
- Fix run-on sentences — break them into clear, readable sentences
- Do NOT add information that wasn't said
- Do NOT change the meaning or observations
- Keep the teacher's tone and intent intact
- Output ONLY the cleaned transcript — no preamble, no explanation"""


def cleanup_transcript(groq_client: Groq, raw_transcript: str) -> str:
    """Stage 1: Clean up raw Whisper output."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": CLEANUP_SYSTEM_PROMPT},
            {"role": "user", "content": f"Raw transcript:\n{raw_transcript}"},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT 2 — Structured Extraction
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured student feedback data
from music teacher voice notes at Udukku Music.

You MUST respond with a single valid JSON object — no markdown, no backticks, no explanation.
Just the raw JSON.

Extraction rules:
1. student_name: Extract the student's name from the transcript.
   If no name is mentioned, use "Unknown Student". Never guess or invent a name.

2. course_level: Extract exact words if stated (e.g. "Beginner", "Grade 4", "Intermediate").
   If not mentioned at all, use exactly the string "Not specified".

3. instrument: Extract if mentioned (e.g. "keyboard", "guitar", "vocals").
   If not mentioned at all, use exactly the string "Not specified".

4. month: Use the provided current month value exactly as given.

5. feedback_summary: Write 2–3 clear, objective sentences summarizing THIS month's
   progress, strengths, and areas of improvement — based ONLY on what the teacher said.
   If the transcript has no feedback content at all, use "Not specified".

6. action_points: Generate exactly 2–3 specific, measurable, forward-looking actions
   for NEXT month. Each must be concrete (e.g. "Practice C major scale at 80bpm for 10 mins daily")
   NOT vague (e.g. "Practice more"). Base these strictly on what the teacher mentioned.
   If there is nothing to base action points on, return ["Not specified"].

CRITICAL: For any field where information is not present in the transcript,
use exactly "Not specified" — never use null, never leave empty, never guess.

Output schema:
{
  "student_name": "string",
  "course_level": "string",
  "instrument": "string",
  "month": "string",
  "feedback_summary": "string",
  "action_points": ["string", "string", "string"]
}"""


def extract_student_data(
    groq_client: Groq,
    cleaned_transcript: str,
    existing_data: dict | None = None,
) -> dict:
    """
    Stage 2: Extract structured student data from cleaned transcript.

    Args:
        groq_client: Groq client instance
        cleaned_transcript: Cleaned transcript text
        existing_data: Optional previous data for this student —
                       any field missing in the new transcript
                       will fall back to the existing value.
    """
    current_month = datetime.now().strftime("%B %Y")

    user_message = f"""Extract student feedback data from the transcript below.

Current month: {current_month}

Transcript:
{cleaned_transcript}"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content.strip()
    data = json.loads(raw_json)

    # ── Fallback: if a field is missing/null/empty, use existing_data value
    # ── or "Not specified" as the final default ──────────────────────────────
    defaults = existing_data or {}
    fallback = "Not specified"

    for field in ["student_name", "course_level", "instrument", "month",
                  "feedback_summary"]:
        val = data.get(field, "")
        if not val or val.strip() == "":
            data[field] = defaults.get(field, fallback)

    # Ensure action_points is a non-empty list
    actions = data.get("action_points", [])
    if isinstance(actions, str):
        actions = [actions]
    actions = [a for a in actions if a and a.strip()]   # remove empty strings
    if not actions:
        actions = defaults.get("action_points", [fallback])
    data["action_points"] = actions[:3]

    # student_name final safety
    if not data.get("student_name") or data["student_name"].strip() == "":
        data["student_name"] = defaults.get("student_name", "Unknown Student")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT 3 — Batch Splitter (edge case: one voice note, many students)
# ─────────────────────────────────────────────────────────────────────────────
BATCH_SPLIT_SYSTEM_PROMPT = """You are a data processing assistant for a music school.
The transcript below may contain feedback for multiple students.

Split the transcript into individual segments — one per student.
Return a JSON array where each element is the feedback text for one student.

Rules:
- Each array element should be a self-contained feedback paragraph for one student
- Do NOT add or invent information
- If only one student is mentioned, return a single-element array
- Output ONLY the JSON array — no explanation

Format: ["feedback for student 1", "feedback for student 2", ...]"""


def split_batch_transcript(groq_client: Groq, transcript: str) -> list[str]:
    """
    Edge case handler: if teacher sends one long note for multiple students,
    split it into per-student segments before extraction.
    """
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": BATCH_SPLIT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
        temperature=0.1,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    segments = json.loads(raw)

    return segments if isinstance(segments, list) else [segments]
