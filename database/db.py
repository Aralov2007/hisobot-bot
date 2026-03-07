from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from config import DATABASE_URL
from database.models import Base, Material
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_default_materials()
    logger.info("Database tables created")


async def seed_default_materials():
    """Default materiallar katalogi"""
    default_materials = [
        ("Mix", "dona", "Asosiy"),
        ("Kabel NYM 3x1.5", "metr", "Kabel"),
        ("Kabel NYM 3x2.5", "metr", "Kabel"),
        ("Kabel VVG 4x6", "metr", "Kabel"),
        ("Kabel VVG 4x10", "metr", "Kabel"),
        ("Kabel VVG 4x16", "metr", "Kabel"),
        ("Rozetka", "dona", "Elektr jihozlari"),
        ("Vyklyuchatel (1 tugmali)", "dona", "Elektr jihozlari"),
        ("Vyklyuchatel (2 tugmali)", "dona", "Elektr jihozlari"),
        ("Avtomat 10A", "dona", "Himoya qurilmalari"),
        ("Avtomat 16A", "dona", "Himoya qurilmalari"),
        ("Avtomat 25A", "dona", "Himoya qurilmalari"),
        ("Avtomat 32A", "dona", "Himoya qurilmalari"),
        ("Avtomat 63A", "dona", "Himoya qurilmalari"),
        ("UZO 25A/30mA", "dona", "Himoya qurilmalari"),
        ("Gofra 16mm", "metr", "Kabel kanali"),
        ("Gofra 20mm", "metr", "Kabel kanali"),
        ("Gofra 25mm", "metr", "Kabel kanali"),
        ("Plastik kabel kanal 20x10", "metr", "Kabel kanali"),
        ("Plastik kabel kanal 40x25", "metr", "Kabel kanali"),
        ("Dübel 6x60", "dona", "Mahkamlash"),
        ("Dübel 8x80", "dona", "Mahkamlash"),
        ("Bolt M6", "dona", "Mahkamlash"),
        ("Elektr lenta", "dona", "Qo'shimcha"),
        ("Izolentsiya", "metr", "Qo'shimcha"),
        ("Klemma bloki", "dona", "Qo'shimcha"),
        ("Schit (6 modulli)", "dona", "Schitlar"),
        ("Schit (12 modulli)", "dona", "Schitlar"),
        ("Schit (24 modulli)", "dona", "Schitlar"),
        ("Boshqa material", "dona", "Boshqa"),
    ]

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Material).limit(1))
        if result.scalar():
            return  # Already seeded

        for name, unit, category in default_materials:
            mat = Material(name=name, unit=unit, category=category)
            session.add(mat)
        await session.commit()
        logger.info("Default materials seeded")


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
