"""Email backend that delivers over HTTPS instead of SMTP.

Render's free plan blocks outbound SMTP (ports 25/465/587), so the stock
`smtp` backend hangs on connect and the request dies. Brevo accepts the same
messages over plain HTTPS on 443, which is not filtered, and its free tier
covers far more mail than a demo needs.

Only the standard library is used, so nothing new lands in requirements.txt.
Errors are raised as `OSError` subclasses (`urllib.error.URLError`), which is
what `ResilientPasswordResetView` already catches — a dead mail provider stays
a logged warning rather than a 500 page.
"""
import json
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

BREVO_ENDPOINT = 'https://api.brevo.com/v3/smtp/email'
TIMEOUT_SECONDS = 15


def _address(value):
    """Split "Name <a@b.c>" into the dict shape Brevo expects."""
    name, email = parseaddr(value)
    payload = {'email': email or value}
    if name:
        payload['name'] = name
    return payload


class BrevoAPIBackend(BaseEmailBackend):
    """Send each message through Brevo's transactional email API."""

    def __init__(self, fail_silently=False, api_key=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, 'BREVO_API_KEY', '')

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            if self.fail_silently:
                return 0
            raise urllib.error.URLError(
                'BREVO_API_KEY is not set, so no mail can be delivered.'
            )

        sent = 0
        for message in email_messages:
            try:
                self._send(message)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent

    def _payload(self, message):
        recipients = [_address(addr) for addr in message.to]
        payload = {
            'sender': _address(message.from_email or settings.DEFAULT_FROM_EMAIL),
            'to': recipients,
            'subject': message.subject,
            'textContent': message.body,
        }

        if message.cc:
            payload['cc'] = [_address(addr) for addr in message.cc]
        if message.bcc:
            payload['bcc'] = [_address(addr) for addr in message.bcc]
        if message.reply_to:
            payload['replyTo'] = _address(message.reply_to[0])

        # A password-reset mail is plain text, but keep HTML alternatives
        # working so the backend suits any message the project sends later.
        for content, mimetype in getattr(message, 'alternatives', []):
            if mimetype == 'text/html':
                payload['htmlContent'] = content
                break

        return payload

    def _send(self, message):
        if not message.to:
            return

        request = urllib.request.Request(
            BREVO_ENDPOINT,
            data=json.dumps(self._payload(message)).encode('utf-8'),
            headers={
                'api-key': self.api_key,
                'content-type': 'application/json',
                'accept': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read()
