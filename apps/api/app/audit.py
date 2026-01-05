# apps/api/app/audit.py
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

_AUDIT_INSERT = text(
    """
        insert into audit_log (org_id, user_id, action, entity_type, entity_id, meta)
        values (:org_id, :user_id, :action, :entity_type, :entity_id, :meta)
        """
).bindparams(bindparam("meta", type_=JSONB))


async def audit_event(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: Optional[UUID] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    await db.execute(
        _AUDIT_INSERT,
        {
            "org_id": org_id,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "meta": meta or {},
        },
    )
