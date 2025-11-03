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
        await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id bigint PRIMARY KEY);")
        
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

# import os
# import aiosqlite

# from typing import Any, List, Optional, Tuple

# from modules.configuration import config


# class Database:
#     def __init__(self):
#         self.conn: Optional[aiosqlite.Connection] = None
#         self.db_path = os.path.join("data", "database.sqlite")
#         os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

#     async def connect(self):
#         self.conn = await aiosqlite.connect(self.db_path)
#         self.conn.row_factory = aiosqlite.Row

#     async def start(self):
#         await self.connect()
#         await self.execute("CREATE TABLE IF NOT EXISTS spams (type varchar, method varchar, channel_id bigint PRIMARY KEY, ments varchar, timestamp varchar);")
#         await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text varchar PRIMARY KEY);")
#         await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text varchar PRIMARY KEY);")
#         await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id bigint PRIMARY KEY, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason varchar);")
#         await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id bigint PRIMARY KEY);")

#         await self.conn.executemany(
#             "INSERT OR IGNORE INTO spamtexts_ordinary (text) VALUES (?)",
#             [(text,) for text in config.DEFAULT_ORDINARY_TEXTS]
#         )

#         await self.conn.executemany(
#             "INSERT OR IGNORE INTO spamtexts_nsfw (text) VALUES (?)",
#             [(text,) for text in config.DEFAULT_NSFW_TEXTS]
#         )

#     async def execute(self, query: str, *args) -> None:
#         if not isinstance(args, (Tuple, List)):
#             args = (args,)
#         async with self.conn.execute(query, args) as cursor:
#             await self.conn.commit()

#     async def fetch(self, query: str, *args) -> List[aiosqlite.Row]:
#         if not isinstance(args, (Tuple, List)):
#             args = (args,)
#         async with self.conn.execute(query, args) as cursor:
#             rows = await cursor.fetchall()
#             return rows

#     async def fetchone(self, query: str, *args) -> Optional[aiosqlite.Row]:
#         if not isinstance(args, (Tuple, List)):
#             args = (args,)
#         async with self.conn.execute(query, args) as cursor:
#             row = await cursor.fetchone()
#             return row

#     async def close(self):
#         if self.conn:
#             await self.conn.close()


# db = Database()