"""Gunicorn settings for the Render free plan.

One worker stays within 512 MB RAM. Eight threads overlap Neon/TLS waits so
a tab click is not stuck behind another request. ``build.sh`` makes the
gunicorn entry point load this file even if the dashboard start command is
still the old one-liner without ``--threads``.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
threads = 8
timeout = 30
keepalive = 5
