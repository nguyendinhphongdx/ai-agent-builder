from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Khởi tạo engine kết nối database async, echo=True khi DEBUG để log SQL
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# Factory tạo session, expire_on_commit=False để giữ dữ liệu sau commit
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency cung cấp database session cho mỗi request.

    Tự động commit khi thành công, rollback khi có lỗi.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
