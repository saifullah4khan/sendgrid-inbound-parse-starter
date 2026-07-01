"""Flask application factory for a SendGrid Inbound Parse receiver.

You give it a callback; it gives you a signed-by-obscurity endpoint that parses
each inbound email and hands you a clean :class:`~inbound_parse.parser.InboundEmail`.
The endpoint always answers 200 quickly so SendGrid does not queue retries.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from flask import Flask, request

from .parser import InboundEmail, parse_inbound

logger = logging.getLogger(__name__)

# A handler takes the parsed email and does whatever you need (store it, kick
# off a job, reply). Its return value is ignored; exceptions are caught.
InboundHandler = Callable[[InboundEmail], None]


def create_app(
    on_email: InboundHandler,
    *,
    url_token: Optional[str] = None,
    require_spf: bool = False,
) -> Flask:
    """Build the receiver app.

    :param on_email: Called with the parsed :class:`InboundEmail` for every
        accepted delivery. Run anything slow in the background: this endpoint
        should return fast.
    :param url_token: If set, the route becomes ``/inbound/<url_token>`` and any
        other path 404s. Inbound Parse does not sign its requests, so a secret
        in the URL is the simplest way to stop random POSTs from being accepted.
        Point your Parse webhook at the full secret URL.
    :param require_spf: When True, reject deliveries whose SPF result is not a
        ``pass``. Off by default because legitimate forwarders can fail SPF.
    """
    app = Flask(__name__)
    route = f"/inbound/{url_token}" if url_token else "/inbound"

    @app.post(route)
    def inbound():
        email = parse_inbound(request.form, request.files)

        if require_spf and not email.passed_spf():
            logger.warning(
                "Rejected inbound email from %s: SPF=%r",
                email.sender_address(),
                email.spf,
            )
            # Still 200 so SendGrid does not retry a message we deliberately
            # dropped; the body records why.
            return {"status": "rejected", "reason": "spf_failed"}, 200

        try:
            on_email(email)
        except Exception:  # noqa: BLE001
            # Log and still return 200. Returning 5xx would make SendGrid retry
            # the same message, which rarely helps and can cause duplicates.
            logger.exception(
                "Inbound email handler raised for message from %s to %s.",
                email.sender_address(),
                email.recipient_address(),
            )
            return {"status": "error"}, 200

        return {"status": "accepted"}, 200

    return app
