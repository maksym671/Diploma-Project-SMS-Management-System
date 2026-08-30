"""Gunicorn: one worker, eight threads (Render free plan)."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
threads = 8
timeout = 30
keepalive = 5
