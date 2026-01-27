import os
from typing import Any, List, Optional

import aiosqlite

# import asyncpg
# import psycopg2
# import sqlalchemy.exc

from modules.configuration import config

# Тип базы данных
USE_SQLITE = True  # False для использования PostgreSQL

class Database:
    def __init__(self):
        if USE_SQLITE:
            self.conn: Optional[aiosqlite.Connection] = None
        # else:
        #     self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        if USE_SQLITE:
            # Создаём директорию data, если её нет
            os.makedirs('data', exist_ok=True)
            self.conn = await aiosqlite.connect('data/database.db')
            # Включаем поддержку внешних ключей
            await self.conn.execute("PRAGMA foreign_keys = ON")
        # else:
        #     self.pool = await asyncpg.create_pool(
        #         config.DATABASE_URL.get_secret_value(),
        #         min_size=1,
        #         max_size=10,
        #         max_queries=50000,
        #         max_inactive_connection_lifetime=300,  # 5 минут
        #         command_timeout=60,
        #         server_settings={
        #             'application_name': 'LittleAngelBot',
        #             'jit': 'off'
        #         }
        #     )
    
    async def _ensure_connection(self):
        """Проверяет соединение и переподключается при необходимости"""
        if USE_SQLITE:
            if self.conn is None:
                await self.connect()
        # else:
        #     if self.pool is None or self.pool._closed:
        #         await self.connect()
    
    async def start(self):
        await self.connect()
        
        if USE_SQLITE:
            # SQLite версии запросов
            await self.execute("CREATE TABLE IF NOT EXISTS spams (type TEXT, method TEXT, channel_id INTEGER UNIQUE, guild_id INTEGER PRIMARY KEY, ments TEXT, timestamp TEXT);")
            await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text TEXT PRIMARY KEY);")
            await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text TEXT PRIMARY KEY);")
            await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id INTEGER PRIMARY KEY, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT);")
            await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id INTEGER PRIMARY KEY);")
            await self.execute("CREATE TABLE IF NOT EXISTS ipou_reconstructions (number INTEGER);")
            
            for text in config.DEFAULT_ORDINARY_TEXTS:
                await self.execute("INSERT OR IGNORE INTO spamtexts_ordinary (text) VALUES (?);", text)
            for text in config.DEFAULT_NSFW_TEXTS:
                await self.execute("INSERT OR IGNORE INTO spamtexts_nsfw (text) VALUES (?);", text)
        # else:
        #     # PostgreSQL версии запросов
        #     await self.execute("CREATE TABLE IF NOT EXISTS spams (type varchar, method varchar, channel_id bigint UNIQUE, guild_id bigint PRIMARY KEY, ments varchar, timestamp varchar);")
        #     await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text varchar PRIMARY KEY);")
        #     await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text varchar PRIMARY KEY);")
        #     await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id bigint PRIMARY KEY, blocked_at TIMESTAMP DEFAULT NOW(), reason varchar);")
        #     await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id bigint PRIMARY KEY);")
        #     await self.executemany(
        #         "INSERT INTO spamtexts_ordinary (text) VALUES ($1) ON CONFLICT DO NOTHING;",
        #         [(text,) for text in config.DEFAULT_ORDINARY_TEXTS]
        #     )
        #     await self.executemany(
        #         "INSERT INTO spamtexts_nsfw (text) VALUES ($1) ON CONFLICT DO NOTHING;",
        #         [(text,) for text in config.DEFAULT_NSFW_TEXTS]
        #     )
        
    async def execute(self, query: str, *args) -> str:
        await self._ensure_connection()
        
        if USE_SQLITE:
            try:
                cursor = await self.conn.execute(query, args)
                await self.conn.commit()
                return f"Executed: {cursor.rowcount} rows affected"
            except Exception as e:
                await self.conn.rollback()
                raise
        # else:
        #     retry_count = 0
        #     max_retries = 3
        #     
        #     while retry_count < max_retries:
        #         try:
        #             async with self.pool.acquire() as conn:
        #                 connection = typing.cast(asyncpg.Connection, conn)
        #                 return await connection.execute(query, *args)
        #         except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError, sqlalchemy.exc.OperationalError, psycopg2.OperationalError) as e:
        #             retry_count += 1
        #             if retry_count >= max_retries:
        #                 raise
        #             await asyncio.sleep(0.5 * retry_count)
        #             await self.connect()
    
    async def executemany(self, query: str, args_list: List[Any]) -> None:
        await self._ensure_connection()
        
        if USE_SQLITE:
            try:
                await self.conn.executemany(query, args_list)
                await self.conn.commit()
            except Exception as e:
                await self.conn.rollback()
                raise
        # else:
        #     retry_count = 0
        #     max_retries = 3
        #     
        #     while retry_count < max_retries:
        #         try:
        #             async with self.pool.acquire() as conn:
        #                 connection = typing.cast(asyncpg.Connection, conn)
        #                 await connection.executemany(query, args_list)
        #                 return
        #         except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError, psycopg2.OperationalError, sqlalchemy.exc.OperationalError) as e:
        #             retry_count += 1
        #             if retry_count >= max_retries:
        #                 raise
        #             await asyncio.sleep(0.5 * retry_count)
        #             await self.connect()
    
    async def fetch(self, query: str, *args) -> List[Any]:
        await self._ensure_connection()
        
        if USE_SQLITE:
            cursor = await self.conn.execute(query, args)
            rows = await cursor.fetchall()
            return rows
        # else:
        #     retry_count = 0
        #     max_retries = 3
        #     
        #     while retry_count < max_retries:
        #         try:
        #             async with self.pool.acquire() as conn:
        #                 connection = typing.cast(asyncpg.Connection, conn)
        #                 return await connection.fetch(query, *args)
        #         except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError) as e:
        #             retry_count += 1
        #             if retry_count >= max_retries:
        #                 raise
        #             await asyncio.sleep(0.5 * retry_count)
        #             await self.connect()
    
    async def fetchone(self, query: str, *args) -> Optional[Any]:
        await self._ensure_connection()
        
        if USE_SQLITE:
            sqlite_query = query.replace('$1', '?').replace('$2', '?').replace('$3', '?')
            cursor = await self.conn.execute(sqlite_query, args)
            row = await cursor.fetchone()
            return row
        # else:
        #     retry_count = 0
        #     max_retries = 3
        #     
        #     while retry_count < max_retries:
        #         try:
        #             async with self.pool.acquire() as conn:
        #                 connection = typing.cast(asyncpg.Connection, conn)
        #                 return await connection.fetchrow(query, *args)
        #         except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionResetError) as e:
        #             retry_count += 1
        #             if retry_count >= max_retries:
        #                 raise
        #             await asyncio.sleep(0.5 * retry_count)
        #             await self.connect()
    
    async def close(self):
        if USE_SQLITE:
            if self.conn:
                await self.conn.close()
        # else:
        #     if self.pool:
        #         await self.pool.close()
    
    async def get_ipou_reconstruction_count(self) -> int:
        if USE_SQLITE:
            row = await self.fetchone("SELECT number FROM ipou_reconstructions ORDER BY number DESC LIMIT 1;")
            if row:
                await self.execute("UPDATE ipou_reconstructions SET number = number + 1;")
                return row['number']
            await self.execute("INSERT INTO ipou_reconstructions (number) VALUES (1);")
            return 1
        # else:
        #     row = await self.fetchone("SELECT number FROM ipou_reconstructions ORDER BY number DESC LIMIT 1;")
        #     if row:
        #         await self.execute("UPDATE ipou_reconstructions SET number = number + 1;")
        #         return row['number']
        #     await self.execute("INSERT INTO ipou_reconstructions (number) VALUES (1);")
        #     return 1

db = Database()