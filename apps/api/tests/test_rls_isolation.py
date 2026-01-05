# apps/api/tests/test_rls_isolation.py

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    pytest.skip("DATABASE_URL not set; skipping RLS tests", allow_module_level=True)

async def _set_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        text("select set_config('app.user_id', :uid, true)"),
        {"uid": str(user_id)},
    )


@pytest.mark.asyncio
async def test_rls_blocks_cross_org_reads():
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    org_name_a = f"Org A {uuid.uuid4()}"
    org_name_b = f"Org B {uuid.uuid4()}"

    async with Session() as db:
        # Defensive cleanup in case DB is dirty from previous runs
        await db.execute(
            text("delete from org_members where user_id in (:a, :b)"),
            {"a": user_a, "b": user_b},
        )

        org_a = (
            await db.execute(
                text("insert into orgs(name) values(:n) returning id"),
                {"n": org_name_a},
            )
        ).scalar_one()
        org_b = (
            await db.execute(
                text("insert into orgs(name) values(:n) returning id"),
                {"n": org_name_b},
            )
        ).scalar_one()

        await db.execute(
            text(
                "insert into org_members(org_id, user_id, role) values (:o, :u, 'member')"
            ),
            {"o": org_a, "u": user_a},
        )
        await db.execute(
            text(
                "insert into org_members(org_id, user_id, role) values (:o, :u, 'member')"
            ),
            {"o": org_b, "u": user_b},
        )
        await db.commit()

    # Insert TA as user_a into org_a
    async with Session() as db:
        await _set_user(db, user_a)
        t_a = (
            await db.execute(
                text(
                    "insert into tournaments(name, org_id) values ('TA', :org) returning id"
                ),
                {"org": org_a},
            )
        ).scalar_one()
        await db.commit()

    # Insert TB as user_b into org_b
    async with Session() as db:
        await _set_user(db, user_b)
        t_b = (
            await db.execute(
                text(
                    "insert into tournaments(name, org_id) values ('TB', :org) returning id"
                ),
                {"org": org_b},
            )
        ).scalar_one()
        await db.commit()

    # Read as user_a: must NOT see TB
    async with Session() as db:
        await _set_user(db, user_a)

        # Count total visible rows among the two IDs
        rows = (
            (
                await db.execute(
                    text("select id from tournaments where id = any(:ids)"),
                    {"ids": [t_a, t_b]},
                )
            )
            .scalars()
            .all()
        )

        assert t_a in rows
        assert t_b not in rows
        assert len(rows) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_rls_blocks_cross_org_write():
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    org_name_a = f"Org A2 {uuid.uuid4()}"
    org_name_b = f"Org B2 {uuid.uuid4()}"

    async with Session() as db:
        await db.execute(
            text("delete from org_members where user_id in (:a, :b)"),
            {"a": user_a, "b": user_b},
        )

        org_a = (
            await db.execute(
                text("insert into orgs(name) values(:n) returning id"),
                {"n": org_name_a},
            )
        ).scalar_one()
        org_b = (
            await db.execute(
                text("insert into orgs(name) values(:n) returning id"),
                {"n": org_name_b},
            )
        ).scalar_one()

        await db.execute(
            text(
                "insert into org_members(org_id, user_id, role) values (:o, :u, 'member')"
            ),
            {"o": org_a, "u": user_a},
        )
        await db.execute(
            text(
                "insert into org_members(org_id, user_id, role) values (:o, :u, 'member')"
            ),
            {"o": org_b, "u": user_b},
        )
        await db.commit()

    async with Session() as db:
        await _set_user(db, user_a)

        # user_a attempts to write into org_b (should be blocked by RLS WITH CHECK)
        with pytest.raises(Exception):
            await db.execute(
                text(
                    "insert into tournaments(name, org_id) values ('SHOULD_FAIL', :org)"
                ),
                {"org": org_b},
            )
            await db.commit()

    await engine.dispose()
