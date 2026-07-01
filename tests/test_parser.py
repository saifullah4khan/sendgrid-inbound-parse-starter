"""Tests for the Inbound Parse form parser."""

from __future__ import annotations

import io
import json

from inbound_parse import parse_inbound


class FakeUpload:
    """Stand-in for a Werkzeug FileStorage."""

    def __init__(self, filename, content_type, content):
        self.filename = filename
        self.content_type = content_type
        self._stream = io.BytesIO(content)

    def read(self):
        return self._stream.read()


def sample_form():
    return {
        "from": "Jane Doe <jane@example.com>",
        "to": "support@myapp.com",
        "subject": "Help please",
        "text": "My widget is broken.",
        "html": "<p>My widget is broken.</p>",
        "envelope": json.dumps({"to": ["support@myapp.com"], "from": "jane@example.com"}),
        "SPF": "pass",
        "dkim": "{@example.com : pass}",
        "charsets": json.dumps({"subject": "UTF-8", "text": "UTF-8"}),
    }


def test_parses_core_fields():
    email = parse_inbound(sample_form())
    assert email.subject == "Help please"
    assert email.text == "My widget is broken."
    assert email.html == "<p>My widget is broken.</p>"


def test_extracts_bare_addresses():
    email = parse_inbound(sample_form())
    assert email.sender_address() == "jane@example.com"
    assert email.recipient_address() == "support@myapp.com"


def test_parses_envelope_and_charsets_json():
    email = parse_inbound(sample_form())
    assert email.envelope["from"] == "jane@example.com"
    assert email.charsets["subject"] == "UTF-8"


def test_spf_helper():
    assert parse_inbound(sample_form()).passed_spf() is True
    form = sample_form()
    form["SPF"] = "softfail"
    assert parse_inbound(form).passed_spf() is False


def test_malformed_envelope_does_not_raise():
    form = sample_form()
    form["envelope"] = "{not valid json"
    email = parse_inbound(form)
    assert email.envelope == {}


def test_missing_fields_default_empty():
    email = parse_inbound({})
    assert email.subject == ""
    assert email.attachments == []
    assert email.envelope == {}


def test_attachments_are_collected():
    files = {
        "attachment1": FakeUpload("photo.png", "image/png", b"\x89PNG..."),
        "attachment2": FakeUpload("notes.txt", "text/plain", b"hello"),
        "not_an_attachment": FakeUpload("x", "text/plain", b"ignored"),
    }
    email = parse_inbound(sample_form(), files)
    names = sorted(a.filename for a in email.attachments)
    assert names == ["notes.txt", "photo.png"]
    txt = next(a for a in email.attachments if a.filename == "notes.txt")
    assert txt.content == b"hello"
    assert txt.size == 5
