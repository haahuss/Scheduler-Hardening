from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .routes import router
from .middleware_body_limit import BodySizeLimitMiddleware
from .middleware_rate_limit import RateLimitMiddleware

app = FastAPI(title="Scheduler Hardening API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BodySizeLimitMiddleware, max_bytes=256_000)  # ~256KB
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)


app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
