"""Parse the multipart form SendGrid Inbound Parse posts to your endpoint.

SendGrid delivers an inbound email as an ``application/x-www-form-urlencoded``
or ``multipart/form-data`` POST. The useful fields are spread across form
values (``to``, ``from``, ``subject``, ``text``, ``html``, ``envelope``,
``SPF``, ``dkim``, ``charsets``) and, when attachments are present, file parts
named ``attachment1``, ``attachment2``, and so on. This module turns that into
one tidy :class:`InboundEmail` object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from email.utils import parseaddr
from typing import Any, Mapping, Optional


@dataclass
class Attachment:
    """A single inbound attachment."""

    filename: str
    content_type: str
    content: bytes

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass
class InboundEmail:
    """A parsed inbound email.

    ``sender`` and ``recipient`` are the raw header values (which may look like
    ``"Jane Doe <jane@example.com>"``); use :meth:`sender_address` and
    :meth:`recipient_address` for just the bare address.
    """

    sender: str
    recipient: str
    subject: str
    text: str
    html: str
    envelope: dict = field(default_factory=dict)
    spf: str = ""
    dkim: str = ""
    charsets: dict = field(default_factory=dict)
    attachments: list = field(default_factory=list)

    def sender_address(self) -> str:
        return parseaddr(self.sender)[1]

    def recipient_address(self) -> str:
        return parseaddr(self.recipient)[1]

    def passed_spf(self) -> bool:
        """True when SendGrid reported an SPF ``pass`` for the sending server."""
        return self.spf.strip().lower() == "pass"


def _load_json(raw: Optional[str]) -> dict:
    """Parse a JSON form field, returning an empty dict on anything unexpected.

    SendGrid sends ``envelope`` and ``charsets`` as JSON strings, but a
    malformed value must never blow up the whole parse.
    """
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def parse_inbound(
    form: Mapping[str, str],
    files: Optional[Mapping[str, Any]] = None,
) -> InboundEmail:
    """Build an :class:`InboundEmail` from a request's form values and files.

    :param form: The form mapping (in Flask, ``request.form``).
    :param files: The uploaded files mapping (in Flask, ``request.files``);
        each value must expose ``filename``, ``content_type``/``mimetype``, and
        ``read()``. ``None`` means no attachments.
    """
    files = files or {}

    email = InboundEmail(
        sender=form.get("from", ""),
        recipient=form.get("to", ""),
        subject=form.get("subject", ""),
        text=form.get("text", ""),
        html=form.get("html", ""),
        envelope=_load_json(form.get("envelope")),
        spf=form.get("SPF", "") or form.get("spf", ""),
        dkim=form.get("dkim", ""),
        charsets=_load_json(form.get("charsets")),
    )

    for key in files:
        # SendGrid names attachment parts attachment1, attachment2, ...
        if not key.startswith("attachment"):
            continue
        storage = files[key]
        content_type = (
            getattr(storage, "content_type", None)
            or getattr(storage, "mimetype", None)
            or "application/octet-stream"
        )
        email.attachments.append(
            Attachment(
                filename=getattr(storage, "filename", "") or key,
                content_type=content_type,
                content=storage.read(),
            )
        )

    return email
