import os
import asyncpg

from typing import Any, List, Optional

from modules.configuration import config

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(config.DATABASE_URL.get_secret_value())

    async def start(self):
        await self.connect()
        await self.execute("CREATE TABLE IF NOT EXISTS spams (type varchar, method varchar, channel_id bigint PRIMARY KEY, ments varchar, timestamp varchar);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text varchar PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text varchar PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id bigint PRIMARY KEY, blocked_at TIMESTAMP DEFAULT NOW(), reason varchar);")
        await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id bigint PRIMARY_KEY);")
        
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