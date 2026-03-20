from contextvars import ContextVar
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from typing import AsyncGenerator
from config.settings import settings

# Global Context for storing current Tenant ID
_tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="public")

def get_current_tenant() -> str:
    return _tenant_id_ctx.get()

def set_current_tenant(tenant_id: str):
    _tenant_id_ctx.set(tenant_id)

# Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Session Factory
async_session_factory = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get a database session with the search_path set to the current tenant.
    """
    tenant_id = get_current_tenant()
    async with async_session_factory() as session:
        # Set the search path to the tenant schema (and public as fallback)
        await session.execute(text(f"SET search_path TO {tenant_id}, public"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
