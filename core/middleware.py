"""Server-Timing header: app time, database time, statement count."""
import time

from django.db import connection


class _DatabaseTimer:
    """Time SQL via execute_wrapper so it works with DEBUG=False."""

    def __init__(self):
        self.seconds = 0.0
        self.statements = 0

    def __call__(self, execute, sql, params, many, context):
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.seconds += time.perf_counter() - started
            self.statements += 1


class ServerTimingMiddleware:
    """Add Server-Timing: app / db durations and how many statements ran."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timer = _DatabaseTimer()
        started = time.perf_counter()
        with connection.execute_wrapper(timer):
            response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000

        response['Server-Timing'] = (
            f'app;dur={elapsed_ms:.1f}, '
            f'db;dur={timer.seconds * 1000:.1f}, '
            f'sql;desc="{timer.statements} statements";dur=0'
        )
        return response
