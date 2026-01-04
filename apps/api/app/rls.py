# apps/api/app/rls.py
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def require_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> UUID:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="Missing X-User-Id")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id")

async def set_rls_identity(db: AsyncSession, user_id: UUID) -> None:
    # IMPORTANT: set_config(..., false) makes it session-level so it persists across commits
    await db.execute(
        text("select set_config('app.user_id', :uid, false)"),
        {"uid": str(user_id)},
    )
