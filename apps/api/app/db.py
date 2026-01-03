from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .settings import settings

# Async SQLAlchemy engine
engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# FastAPI dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
