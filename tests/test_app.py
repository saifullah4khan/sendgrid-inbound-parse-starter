"""Tests for the Flask receiver via the test client."""

from __future__ import annotations

import io

from inbound_parse import create_app


def form_data(**overrides):
    data = {
        "from": "Jane Doe <jane@example.com>",
        "to": "support@myapp.com",
        "subject": "Help please",
        "text": "broken widget",
        "SPF": "pass",
    }
    data.update(overrides)
    return data


def test_accepts_a_delivery_and_calls_handler():
    received = []
    app = create_app(lambda email: received.append(email))
    client = app.test_client()

    resp = client.post("/inbound", data=form_data())
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "accepted"
    assert len(received) == 1
    assert received[0].subject == "Help please"


def test_url_token_guards_the_route():
    app = create_app(lambda e: None, url_token="s3cret")
    client = app.test_client()

    assert client.post("/inbound").status_code == 404  # no token
    assert client.post("/inbound/s3cret", data=form_data()).status_code == 200


def test_handler_exception_still_returns_200():
    def boom(email):
        raise RuntimeError("db down")

    app = create_app(boom)
    resp = app.test_client().post("/inbound", data=form_data())
    # 200 keeps SendGrid from retrying; the body signals the error.
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "error"


def test_require_spf_rejects_softfail():
    received = []
    app = create_app(lambda e: received.append(e), require_spf=True)
    client = app.test_client()

    resp = client.post("/inbound", data=form_data(SPF="softfail"))
    assert resp.status_code == 200
    assert resp.get_json()["reason"] == "spf_failed"
    assert received == []  # handler not called


def test_attachment_upload_is_parsed():
    received = []
    app = create_app(lambda e: received.append(e))
    client = app.test_client()

    data = form_data()
    data["attachment1"] = (io.BytesIO(b"file-bytes"), "doc.pdf", "application/pdf")
    resp = client.post("/inbound", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert received[0].attachments[0].filename == "doc.pdf"
    assert received[0].attachments[0].content == b"file-bytes"
