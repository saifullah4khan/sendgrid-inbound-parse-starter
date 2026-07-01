# sendgrid-inbound-parse-starter

A minimal, well-documented Flask starter for receiving inbound email through
SendGrid's Inbound Parse webhook.

## The problem

SendGrid's Inbound Parse feature turns an email sent to your domain into an
HTTP POST to your server. It is genuinely useful (support inboxes, reply-by-
email, ticketing) but the first time you wire it up you hit the same friction:
the payload is a multipart form with fields spread across `to`, `from`,
`envelope`, `SPF`, `charsets`, and file parts named `attachment1`,
`attachment2`, and the webhook is unauthenticated, so you have to think about
who can POST to it and how not to trigger retry storms.

This starter handles that boilerplate. You provide a callback; it parses each
delivery into a clean object, guards the route, and returns the right status
code so SendGrid behaves.

## Quickstart

```bash
pip install sendgrid-inbound-parse-starter
```

```python
from inbound_parse import create_app, InboundEmail

def handle(email: InboundEmail) -> None:
    print(email.sender_address(), "->", email.subject)
    # store it, open a ticket, enqueue a job, etc.

app = create_app(handle, url_token="your-secret")

if __name__ == "__main__":
    app.run(port=8000)
```

Then in SendGrid, set the Inbound Parse host and point the destination URL at
`https://your-domain.com/inbound/your-secret`. In development, expose your
local port with a tunnel (for example ngrok) and use that URL.

There is a runnable demo:

```bash
python example.py
```

## What you get

The callback receives an `InboundEmail` with `sender`, `recipient`, `subject`,
`text`, `html`, the parsed `envelope` and `charsets`, the `spf` and `dkim`
results, and a list of `attachments` (each with `filename`, `content_type`,
`content` bytes, and `size`). The raw `sender`/`recipient` keep the full header
value; `sender_address()` and `recipient_address()` give you just the address.

## Design decisions

**The endpoint always returns 200 quickly.** SendGrid retries a delivery if it
gets a non-2xx response, so a slow or failing handler can turn one email into
several. This starter parses the message, calls your handler, and returns 200
even when the handler raises (the failure is logged and reported in the body).
Do anything slow in the background; treat the webhook as "accept and hand off."

**A secret in the URL is the default guard.** Inbound Parse requests are not
signed, so there is no signature to verify. The simplest effective protection
is an unguessable path segment: set `url_token` and the route becomes
`/inbound/<token>`, with every other path returning 404. Keep the token out of
logs and source control.

**SPF checking is available but off by default.** SendGrid reports the SPF
result and you can require a `pass` with `require_spf=True`, but it is opt-in
because legitimate forwarded mail (mailing lists, aliases) frequently fails
SPF, and rejecting it by default would silently drop real messages.

**Malformed fields degrade instead of crashing.** The `envelope` and
`charsets` fields are JSON strings in practice, but a malformed value parses to
an empty dict rather than raising, so one odd delivery can't take the endpoint
down.

**Parsing is separate from the web layer.** `parse_inbound(form, files)` is a
plain function with no Flask dependency, so it is easy to unit test and reuse
if you are not on Flask. The app factory is a thin wrapper around it.

## Configuration

| `create_app` argument | Default | Meaning |
| --- | --- | --- |
| `on_email` | required | Callback invoked with each parsed `InboundEmail`. |
| `url_token` | `None` | Secret path segment; route becomes `/inbound/<token>`. |
| `require_spf` | `False` | Reject deliveries whose SPF result is not `pass`. |

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite covers the parser (core fields, address extraction, envelope and
charset JSON, malformed input, and attachment collection) and the Flask app
(accepting a delivery, the URL-token guard, the always-200 behavior on a
handler error, SPF rejection, and a real multipart attachment upload).

## License

MIT. See [LICENSE](LICENSE).
