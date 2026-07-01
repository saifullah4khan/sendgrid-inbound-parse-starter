"""Runnable demo of the SendGrid Inbound Parse receiver.

Starts a receiver on port 8000 that prints a summary of each inbound email.
Point a SendGrid Inbound Parse webhook at http://<your-host>:8000/inbound/demo
(or use a tunnel like ngrok in development), then send a test email.

    python example.py
"""

from __future__ import annotations

from inbound_parse import InboundEmail, create_app


def handle(email: InboundEmail) -> None:
    print("--- inbound email ---")
    print("from:   ", email.sender_address())
    print("to:     ", email.recipient_address())
    print("subject:", email.subject)
    print("spf:    ", email.spf)
    print("body:   ", (email.text or "")[:200])
    for attachment in email.attachments:
        print(f"attachment: {attachment.filename} ({attachment.size} bytes)")


def main() -> None:
    app = create_app(handle, url_token="demo")
    print("Receiver on http://localhost:8000/inbound/demo")
    app.run(port=8000)


if __name__ == "__main__":
    main()
