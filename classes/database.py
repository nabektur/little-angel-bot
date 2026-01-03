import psycopg2
import sqlalchemy.exc
import asyncpg
import typing
import asyncio

from typing                import Any, List, Optional
from modules.configuration import config

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            config.DATABASE_URL.get_secret_value(),
            min_size=1,
            max_size=10,
            max_queries=50000,
            max_inactive_connection_lifetime=300,  # 5 минут
            command_timeout=60,
            server_settings={
                'application_name': 'LittleAngelBot',
                'jit': 'off'
            }
        )
    
    async def _ensure_connection(self):
        """Проверяет соединение и переподключается при необходимости"""
        if self.pool is None or self.pool._closed:
            await self.connect()
    
    async def start(self):
        await self.connect()
        await self.execute("CREATE TABLE IF NOT EXISTS spams (type varchar, method varchar, channel_id bigint UNIQUE, guild_id bigint PRIMARY KEY, ments varchar, timestamp varchar);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text varchar PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text varchar PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id bigint PRIMARY KEY, blocked_at TIMESTAMP DEFAULT NOW(), reason varchar);")
        await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id bigint PRIMARY KEY);")
        await self.executemany(
            "INSERT INTO spamtexts_ordinary (text) VALUES ($1) ON CONFLICT DO NOTHING;",
            [(text,) for text in config.DEFAULT_ORDINARY_TEXTS]
        )
        await self.executemany(
            "INSERT INTO spamtexts_nsfw (text) VALUES ($1) ON CONFLICT DO NOTHING;",
            [(text,) for text in config.DEFAULT_NSFW_TEXTS]
        )
        
    async def execute(self, query: str, *args) -> str:
        await self._ensure_connection()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with self.pool.acquire() as conn:
                    connection = typing.cast(asyncpg.Connection, conn)
                    return await connection.execute(query, *args)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError, sqlalchemy.exc.OperationalError, psycopg2.OperationalError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(0.5 * retry_count)
                await self.connect()
    
    async def executemany(self, query: str, args_list: List[Any]) -> None:
        await self._ensure_connection()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with self.pool.acquire() as conn:
                    connection = typing.cast(asyncpg.Connection, conn)
                    await connection.executemany(query, args_list)
                    return
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError, psycopg2.OperationalError, sqlalchemy.exc.OperationalError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(0.5 * retry_count)
                await self.connect()
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        await self._ensure_connection()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with self.pool.acquire() as conn:
                    connection = typing.cast(asyncpg.Connection, conn)
                    return await connection.fetch(query, *args)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(0.5 * retry_count)
                await self.connect()
    
    async def fetchone(self, query: str, *args) -> Optional[asyncpg.Record]:
        await self._ensure_connection()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                async with self.pool.acquire() as conn:
                    connection = typing.cast(asyncpg.Connection, conn)
                    return await connection.fetchrow(query, *args)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(0.5 * retry_count)
                await self.connect()
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def get_ipou_reconstruction_count(self) -> int:
        row = await self.fetchone("SELECT number FROM ipou_reconstructions ORDER BY number DESC LIMIT 1;")
        if row:
            await self.execute("UPDATE ipou_reconstructions SET number = number + 1;")
            return row['number']
        await self.execute("INSERT INTO ipou_reconstructions (number) VALUES (1);")
        return 1

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