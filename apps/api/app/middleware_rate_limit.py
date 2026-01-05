from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple fixed-window limiter using a per-key timestamp deque.
    Good enough for a demo; not distributed.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits = defaultdict(deque)  # key -> deque[timestamps]
        self._lock = asyncio.Lock()

    def _key(self, request: Request) -> str:
        # Prefer authenticated identity, else fallback to IP
        user = request.headers.get("x-user-id")
        if user:
            return f"user:{user}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next):
        key = self._key(request)
        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()

            if len(q) >= self.max_requests:
                return JSONResponse(
                    {"detail": "Rate limit exceeded. Try again later."}, status_code=429
                )

            q.append(now)

        return await call_next(request)
