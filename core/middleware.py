"""Request instrumentation.

The application renders every page in single-digit milliseconds locally while
the deployed site answered in over a second, and guessing at the difference
wasted a round of work. This measures it at the source instead: how long the
server spent, and how much of that was spent waiting on the database.
"""
import time

from django.db import connection


class _DatabaseTimer:
    """Times every statement through Django's execute_wrapper hook.

    connection.queries only fills when DEBUG is on, which is exactly when the
    numbers do not matter. This works on the deployed site.
    """

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
    """Report server time and database time in a Server-Timing header.

    Browsers show these in the network panel beside the network cost, so a
    slow page can be attributed without a profiler on the box. Only durations
    and a statement count are reported — no query text and no data.
    """

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
