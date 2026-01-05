from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = 256_000):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        # Fast path: Content-Length present
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse(
                        {
                            "detail": f"Request body too large (>{self.max_bytes} bytes)."
                        },
                        status_code=413,
                    )
            except ValueError:
                # ignore malformed content-length; fall back to read
                pass

        # Safer path: read body once, enforce limit
        body = await request.body()
        if len(body) > self.max_bytes:
            return JSONResponse(
                {"detail": f"Request body too large (>{self.max_bytes} bytes)."},
                status_code=413,
            )

        # Re-inject body so downstream can read it
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # Starlette pattern for replaying body
        return await call_next(request)
