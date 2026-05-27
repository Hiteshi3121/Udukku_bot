"""
Udukku Music – Student Feedback WhatsApp Bot
=============================================
Flow:
  Teacher sends WhatsApp voice note
  → Twilio webhook → FastAPI
  → Groq Whisper transcription
  → Groq LLaMA structured extraction (name extracted from audio)
  → HTML student page saved locally (served via /pages/)
  → Google Sheets row logged (non-fatal if it fails)
  → WhatsApp reply with page link
"""

import os
import httpx
import tempfile
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from twilio.rest import Client as TwilioClient
from groq import Groq
from dotenv import load_dotenv

from app.extractor import extract_student_data, cleanup_transcript
from app.sheets import append_to_sheet
from app.gdocs import create_student_doc
from app.whatsapp import send_whatsapp_reply

load_dotenv()

app = FastAPI(title="Udukku Music Bot")

# ── Serve student HTML pages statically at /pages/ ──────────────────────────
Path("student_pages").mkdir(exist_ok=True)
app.mount("/pages", StaticFiles(directory="student_pages", html=True), name="pages")

twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@app.get("/")
async def health():
    return {"status": "Udukku Music Bot is running ✅"}


@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    NumMedia: str = Form(default="0"),
    MediaUrl0: str = Form(default=None),
    MediaContentType0: str = Form(default=None),
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
):
    """
    Twilio WhatsApp webhook endpoint.
    Triggered every time the teacher sends a message.
    """
    from_number = From

    # ── Guard: must be a voice note (audio media) ──────────────────────────
    has_audio = (
        NumMedia != "0"
        and MediaUrl0 is not None
        and MediaContentType0 is not None
        and "audio" in MediaContentType0
    )

    if not has_audio:
        if Body.strip().lower() in ["hi", "hello", "help", ""]:
            send_whatsapp_reply(
                from_number,
                "👋 *Udukku Music Feedback Bot*\n\n"
                "To generate a student page:\n"
                "1️⃣ Send a voice note about the student\n"
                "2️⃣ Mention the student's name clearly in the voice note\n\n"
                "Example: _'Feedback for Ananya — she is in Grade 4...'_",
            )
        return PlainTextResponse("ok", status_code=200)

    # ── Acknowledge immediately ─────────────────────────────────────────────
    send_whatsapp_reply(
        from_number,
        "🎙️ Voice note received! Processing...\n"
        "This usually takes 15–30 seconds.",
    )

    try:
        # ── Step 1: Download audio from Twilio ──────────────────────────────
        audio_bytes = await download_twilio_audio(MediaUrl0)

        # ── Step 2: Transcribe with Groq Whisper ────────────────────────────
        raw_transcript = transcribe_audio(audio_bytes, MediaContentType0)

        # ── Step 3: Cleanup transcript ──────────────────────────────────────
        clean_transcript = cleanup_transcript(groq_client, raw_transcript)

        # ── Step 4: Extract structured student data (name from audio) ───────
        student_data = extract_student_data(groq_client, clean_transcript)

        # ── Step 5: Create HTML student page ────────────────────────────────
        page_url = create_student_doc(student_data)

        # ── Step 6: Log to Google Sheet (non-critical) ───────────────────────
        try:
            append_to_sheet(student_data, page_url)
        except Exception as sheet_err:
            print(f"⚠️  Sheets logging failed (non-fatal): {sheet_err}")

        # ── Step 7: Reply with success + page link ───────────────────────────
        send_whatsapp_reply(
            from_number,
            f"✅ *Student page created for {student_data['student_name']}!*\n\n"
            f"📋 *Feedback Summary:*\n{student_data['feedback_summary']}\n\n"
            f"🎯 *Action Points:*\n"
            + "\n".join(f"• {ap}" for ap in student_data["action_points"])
            + f"\n\n📄 *Full Page:* {page_url}",
        )

    except Exception as e:
        send_whatsapp_reply(
            from_number,
            f"❌ Something went wrong.\nError: {str(e)}\n\nPlease try again.",
        )
        raise e

    return PlainTextResponse("ok", status_code=200)


async def download_twilio_audio(media_url: str) -> bytes:
    """Download audio file from Twilio media URL (requires auth)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            media_url,
            auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
            follow_redirects=True,
            timeout=30,
        )
        response.raise_for_status()
        return response.content


def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    """Transcribe audio bytes using Groq Whisper."""
    ext_map = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }
    ext = ext_map.get(content_type, ".ogg")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as audio_file:
        transcription = groq_client.audio.transcriptions.create(
            file=(f"audio{ext}", audio_file.read()),
            model="whisper-large-v3",
            language="en",
            response_format="text",
        )

    os.unlink(tmp_path)
    return transcription