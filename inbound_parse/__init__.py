"""sendgrid-inbound-parse-starter: receive inbound email via SendGrid Inbound Parse.

A minimal, documented Flask starter. Point a SendGrid Inbound Parse webhook at
the endpoint, and each inbound email arrives as a parsed
:class:`~inbound_parse.parser.InboundEmail` handed to your callback.
"""

from __future__ import annotations

from .app import create_app
from .parser import Attachment, InboundEmail, parse_inbound

__all__ = ["create_app", "parse_inbound", "InboundEmail", "Attachment"]
