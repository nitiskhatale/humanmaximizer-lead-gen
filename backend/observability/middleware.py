"""
MetricsMiddleware — records per-request latency into the stage_latency histogram.

The route path is used as the stage label so Prometheus can show latency
per endpoint without additional instrumentation in route handlers.
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.metrics import stage_latency


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - t0

        # Use path as stage label, strip query string
        path = request.url.path
        stage_latency.labels(stage=path).observe(elapsed)

        return response
