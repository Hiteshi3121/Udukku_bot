"""
whatsapp.py — Twilio WhatsApp Reply Helper
==========================================
Sends WhatsApp messages back to the teacher via Twilio.
"""

import os
from twilio.rest import Client


def send_whatsapp_reply(to: str, message: str) -> None:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to: Recipient number in format 'whatsapp:+91XXXXXXXXXX'
        message: Message body (supports basic WhatsApp markdown: *bold*, _italic_)
    """
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )

    # Ensure 'whatsapp:' prefix
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"

    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g. whatsapp:+14155238886
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    client.messages.create(
        body=message,
        from_=from_number,
        to=to,
    )
