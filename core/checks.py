"""Deployment checks for the mail configuration.

`manage.py check --deploy` runs these, so a deployment that would silently
swallow password-reset emails is caught before it goes live instead of during
a demo.
"""
from django.conf import settings
from django.core.checks import Warning, register

SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
CONSOLE_BACKEND = 'django.core.mail.backends.console.EmailBackend'
BREVO_BACKEND = 'core.mail.BrevoAPIBackend'

# Domains that no real mail server will accept as a sender.
UNROUTABLE_SUFFIXES = ('.local', '.invalid', '.example', '.test', 'localhost')


@register('mail', deploy=True)
def check_email_configuration(app_configs, **kwargs):
    errors = []

    if settings.DEBUG:
        return errors

    backend = getattr(settings, 'EMAIL_BACKEND', '')

    if backend == CONSOLE_BACKEND:
        errors.append(Warning(
            'Password-reset emails are written to the server log, not sent.',
            hint='Nobody receives a reset link on this deployment. Set '
                 'EMAIL_BACKEND=smtp plus EMAIL_HOST, EMAIL_HOST_USER and '
                 'EMAIL_HOST_PASSWORD to deliver mail for real.',
            id='mail.W001',
        ))

    if backend == BREVO_BACKEND:
        if not getattr(settings, 'BREVO_API_KEY', ''):
            errors.append(Warning(
                'EMAIL_BACKEND is brevo but BREVO_API_KEY is empty.',
                hint='Create an API key at brevo.com (SMTP & API -> API keys) '
                     'and set it in the hosting platform dashboard.',
                id='mail.W005',
            ))

        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        domain = sender.rsplit('@', 1)[-1].rstrip('>').lower()
        if domain.endswith(UNROUTABLE_SUFFIXES):
            errors.append(Warning(
                f'DEFAULT_FROM_EMAIL uses the unroutable domain "{domain}".',
                hint='Brevo only sends from an address verified on the account. '
                     'Verify the sender under Senders & IPs, then use it here.',
                id='mail.W004',
            ))

    if backend == SMTP_BACKEND:
        if not getattr(settings, 'EMAIL_HOST_USER', ''):
            errors.append(Warning(
                'EMAIL_BACKEND is smtp but EMAIL_HOST_USER is empty.',
                hint='Most providers reject unauthenticated mail, so every '
                     'reset request will fail. Set EMAIL_HOST_USER and '
                     'EMAIL_HOST_PASSWORD.',
                id='mail.W002',
            ))
        if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            errors.append(Warning(
                'EMAIL_BACKEND is smtp but EMAIL_HOST_PASSWORD is empty.',
                hint='Set it in the hosting platform dashboard so the secret '
                     'never reaches the repository.',
                id='mail.W003',
            ))

        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        domain = sender.rsplit('@', 1)[-1].rstrip('>').lower()
        if domain.endswith(UNROUTABLE_SUFFIXES):
            errors.append(Warning(
                f'DEFAULT_FROM_EMAIL uses the unroutable domain "{domain}".',
                hint='Providers drop or spam-file mail from a domain that '
                     'cannot receive replies. Use the address that owns the '
                     'SMTP account, e.g. "SMS <your.account@gmail.com>".',
                id='mail.W004',
            ))

    return errors
