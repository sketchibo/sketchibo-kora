import os
import time
import imaplib
import email
import smtplib
from email.message import EmailMessage
from pathlib import Path

ENV_PATH = Path(__file__).with_name(".env")

def load_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

load_env(ENV_PATH)

EMAIL_ADDR = os.environ["KORA_EMAIL"]
EMAIL_PASS = os.environ["KORA_EMAIL_APP_PASSWORD"]
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
POLL_SECONDS = int(os.environ.get("KORA_MAIL_POLL_SECONDS", "10"))

def extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="ignore")
    return ""

def send_reply(to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDR
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_ADDR, EMAIL_PASS)
        smtp.send_message(msg)

def handle_command(subject: str, body: str) -> str:
    s = (subject or "").strip().lower()

    if "status" in s:
        return "KORA online. Mail heartbeat active."

    if "snapshot" in s:
        return "Snapshot command received. Real snapshot wiring comes next."

    if "ask" in s:
        question = body.strip() or "(no body provided)"
        return f"KORA received your question:\n\n{question}\n\nNext step: wire this into kora.py."

    return (
        "KORA mailbox active.\n\n"
        "Use subjects like:\n"
        "- KORA: status\n"
        "- KORA: snapshot\n"
        "- KORA: ask\n"
    )

def check_mail() -> None:
    imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    imap.login(EMAIL_ADDR, EMAIL_PASS)
    imap.select("INBOX")

    status, data = imap.search(None, "(UNSEEN)")
    if status == "OK":
        for num in data[0].split():
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_addr = email.utils.parseaddr(msg.get("From", ""))[1]
            subject = msg.get("Subject", "")
            body = extract_body(msg)

            reply = handle_command(subject, body)
            send_reply(from_addr, f"Re: {subject or 'KORA'}", reply)
            imap.store(num, "+FLAGS", "\\Seen")

    imap.logout()

def main() -> None:
    print(f"[mail_bridge] running; polling every {POLL_SECONDS}s")
    while True:
        try:
            check_mail()
        except Exception as e:
            print(f"[mail_bridge] error: {e}", flush=True)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
