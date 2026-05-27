# Udukku Music — Student Feedback Bot

A WhatsApp voice note → student page pipeline built for the Udukku Music Prompt Engineer Intern assignment.

---
<img width="300" height="1050" alt="1000330692" src="https://github.com/user-attachments/assets/28e624d6-b675-4e90-bd8d-d37d5152c961" />

<img width="250" height="800" alt="1000330696" src="https://github.com/user-attachments/assets/8daacd84-d66a-409f-8f77-bf39741fe725" />

<img width="250" height="800" alt="1000330694" src="https://github.com/user-attachments/assets/ee88378b-85ef-46bb-ab2e-21ceef9535bb" />


## What it does

Teacher sends a WhatsApp voice note → bot automatically generates a formatted student feedback page and sends the link back on WhatsApp.

Each page includes:
- Student name (extracted from audio)
- Course level & instrument
- This month's feedback summary
- 2–3 action points for next month

---

## Pipeline

```
Voice Note (WhatsApp)
      ↓
Twilio Webhook → FastAPI
      ↓
Groq Whisper → Transcript
      ↓
LLaMA 3.3 Prompt 1 → Cleaned Transcript
      ↓
LLaMA 3.3 Prompt 2 → Structured JSON
      ↓
HTML Student Page (saved locally, served via /pages/)
      ↓
WhatsApp Reply with summary + page link
```

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Messaging | Twilio WhatsApp Sandbox |
| Transcription | Groq Whisper |
| Extraction | Groq LLaMA 3.3 70B |
| Backend | FastAPI + uvicorn |
| Output | HTML static pages |
| Logging | Google Sheets (optional) |

---

## Setup

**1. Clone and install**
```bash
git clone https://github.com/your-username/udukku-bot
cd udukku-bot
pip install -r requirements.txt
```

**2. Configure `.env`**
```bash
cp .env.example .env
# Fill in your keys
```

Required keys:
```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
GROQ_API_KEY=
NGROK_URL=https://your-ngrok-url.ngrok-free.dev
TEACHER_NAME=Ms. Priya
```

**3. Run**
```bash
uvicorn app.main:app --reload --port 5678
```

**4. Expose via ngrok** (in a separate terminal)
```bash
ngrok http 5678
```

**5. Set Twilio webhook**

Go to Twilio Console → WhatsApp Sandbox Settings → set "When a message comes in" to:
```
https://your-ngrok-url.ngrok-free.dev/webhook/whatsapp
```

---

## Usage

Send a WhatsApp voice note to the Twilio sandbox number. Mention the student's name naturally in the audio:

> *"Feedback for Ananya — she is in Grade 4, plays keyboard..."*

The bot will reply with a summary and a link to the student's page.

---

## Project Structure

```
udukku_bot/
├── app/
│   ├── main.py          # FastAPI webhook + pipeline orchestration
│   ├── extractor.py     # Prompt engineering — cleanup + extraction
│   ├── gdocs.py         # HTML student page generator
│   ├── sheets.py        # Google Sheets logger
│   └── whatsapp.py      # Twilio reply helper
├── student_pages/       # Generated HTML pages (auto-created)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Author

**Hiteshi Aglawe** — hiteshiaglawe@gmail.com — [github.com/Hiteshi3121](https://github.com/Hiteshi3121)
