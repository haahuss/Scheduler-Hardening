# apps/api/app/deps.py
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import PendingRollbackError

from .db import get_db
from .rls import require_user_id, set_rls_identity


async def get_db_rls(
    user_id=Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    # 1) Bootstrap FIRST (so membership exists before any RLS-protected insert)
    await db.execute(
        text("""
        insert into orgs (name)
        select 'Default Org'
        where not exists (select 1 from orgs)
        """)
    )

    await db.execute(
        text("""
        insert into org_members (org_id, user_id, role)
        select (select id from orgs order by created_at limit 1), :uid, 'owner'
        where not exists (select 1 from org_members where user_id = :uid)
        """),
        {"uid": str(user_id)},
    )

    # 2) Now set identity for the rest of this request/session
    await set_rls_identity(db, user_id)

    try:
        yield db
    finally:
        try:
            await db.rollback()  # clears failed transaction state if any
        except Exception:
            pass

        try:
            await db.execute(text("RESET app.user_id"))
        except PendingRollbackError:
            # session was invalid; nothing to do
            pass
        except Exception:
            pass
