"""
Ganji Protocol - Signal Delivery Layer (Layer 5)
Delivers the signal output to subscribers.

Phase 1: file write + console print
Phase 2: email on HIGH or MEDIUM confidence
Phase 3: webhooks, SMS, REST API

Reference: SYSTEM.md Section 7.2
"""

import json
import logging
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.config import RAW_DATA_FILES

log = logging.getLogger(__name__)

NOTIFY_CONFIDENCES = {"HIGH", "MEDIUM"}


# ─────────────────────────────────────────────
# Delivery Handler 1: File Write (Phase 1)
# ─────────────────────────────────────────────

def deliver_to_file(signal: dict) -> bool:
    """
    Writes the latest signal to a fixed JSON file.
    Overwrites on every run so the file always contains the current signal.
    """
    path = _ROOT / "data" / "latest_signal.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(signal, f, indent=2)
        log.info(f"Signal written to {path}")
        return True
    except Exception as e:
        log.error(f"File delivery failed: {e}")
        return False


# ─────────────────────────────────────────────
# Delivery Handler 2: Console Print (Phase 1)
# ─────────────────────────────────────────────

def deliver_to_console(signal: dict) -> bool:
    """
    Prints a human-readable signal summary to stdout.
    Used for manual monitoring and cron log output.
    """
    confidence = signal["detection"]["confidence"]
    direction  = signal["detection"]["direction"]
    score      = signal["detection"]["cips_score"]
    context    = signal.get("signal_context", "")
    signal_id  = signal["signal_id"]
    timestamp  = signal["timestamp"]

    border = "=" * 60
    print(f"\n{border}")
    print(f"  GANJI PROTOCOL SIGNAL")
    print(f"  {signal_id} | {timestamp}")
    print(f"{border}")
    print(f"  Confidence : {confidence}")
    print(f"  Direction  : {direction}")
    print(f"  CIPS Score : {score}")
    print(f"{border}")
    print(f"  {context}")
    print(f"{border}")
    print(f"  {signal['regulatory_note']}")
    print(f"{border}\n")
    return True


# ─────────────────────────────────────────────
# Delivery Handler 3: Email (Phase 2)
# ─────────────────────────────────────────────

def deliver_to_email(signal: dict) -> bool:
    """
    Sends an email alert when confidence is HIGH or MEDIUM.
    Requires SMTP settings in .env:
      EMAIL_FROM, EMAIL_TO, EMAIL_SMTP_HOST,
      EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_PASS

    Phase 2 feature. Skipped silently if credentials not configured.
    """
    email_from = os.getenv("EMAIL_FROM", "")
    email_to   = os.getenv("EMAIL_TO", "")
    smtp_host  = os.getenv("EMAIL_SMTP_HOST", "")
    smtp_port  = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    smtp_user  = os.getenv("EMAIL_SMTP_USER", "")
    smtp_pass  = os.getenv("EMAIL_SMTP_PASS", "")

    if not all([email_from, email_to, smtp_host, smtp_user, smtp_pass]):
        log.debug("Email delivery: credentials not configured. Skipping.")
        return False

    confidence = signal["detection"]["confidence"]
    if confidence not in NOTIFY_CONFIDENCES:
        log.debug(f"Email delivery: confidence {confidence} below notify threshold. Skipping.")
        return False

    try:
        subject = (
            f"[Ganji Protocol] {confidence} Signal | "
            f"{signal['detection']['direction']} | "
            f"CIPS {signal['detection']['cips_score']}"
        )

        body = f"""
Ganji Protocol Signal Alert
Signal ID : {signal['signal_id']}
Timestamp : {signal['timestamp']}
Pair      : {signal['pair']}

CONFIDENCE : {confidence}
DIRECTION  : {signal['detection']['direction']}
CIPS SCORE : {signal['detection']['cips_score']}

{signal.get('signal_context', '')}

Component Breakdown:
  Z-Score  : {signal['components']['z_score']['value']} (points: {signal['components']['z_score']['points']})
  CPII     : fired={signal['components']['cpii']['fired']} (points: {signal['components']['cpii']['points']})
  GVCI     : {signal['components']['gvci']['gvci_value']} (points: {signal['components']['gvci']['points']})
  NLP Tone : {signal['components']['nlp_tone']['tone']} (points: {signal['components']['nlp_tone']['points']})
  BPPS     : premium={signal['components']['bpps']['premium']} (points: {signal['components']['bpps']['points']})

{signal['regulatory_note']}
        """.strip()

        msg = MIMEMultipart()
        msg["From"]    = email_from
        msg["To"]      = email_to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(email_from, email_to, msg.as_string())

        log.info(f"Email sent to {email_to} | {subject}")
        return True

    except Exception as e:
        log.error(f"Email delivery failed: {e}")
        return False


# ─────────────────────────────────────────────
# Master Delivery Function
# ─────────────────────────────────────────────

def deliver(signal: dict) -> dict:
    """
    Runs all delivery handlers in sequence.
    Returns a summary of delivery results.
    """
    results = {
        "file":    deliver_to_file(signal),
        "console": deliver_to_console(signal),
        "email":   deliver_to_email(signal),
    }
    log.info(f"Delivery complete: {results}")
    return results
