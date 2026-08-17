import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def test():
    url = os.environ['DATABASE_URL']
    engine = create_async_engine(url, connect_args={'ssl': False})
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print('Tables:', tables)
    await engine.dispose()

asyncio.run(test())