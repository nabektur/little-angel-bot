import os
import asyncpg

from typing import Any, List, Optional

from modules.configuration import settings

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(settings.DATABASE_URL.get_secret_value())

    async def start(self):
        await self.connect()
        # await execute("CREATE TABLE IF NOT EXISTS last_responses (dialog_id varchar PRIMARY KEY, last_response_id varchar);")
        # await execute("CREATE TABLE IF NOT EXISTS users_carts (dialog_id varchar PRIMARY KEY, cart varchar);")
        # await execute("CREATE TABLE IF NOT EXISTS users_orders (number integer PRIMARY KEY, dialog_id varchar, address varchar, delivery_time_start varchar, delivery_time_end varchar, additional_comments varchar, cart varchar);")
        
    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchone(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def close(self):
        if self.pool:
            await self.pool.close()

db = Database()