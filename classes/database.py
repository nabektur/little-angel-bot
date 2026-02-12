import os
from typing import Any, List, Optional

import aiosqlite

from modules.configuration import CONFIG

class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        os.makedirs('data', exist_ok=True)
        self.conn = await aiosqlite.connect('data/database.db')

        await self.conn.execute("PRAGMA foreign_keys = ON")
    
    async def _ensure_connection(self):
        if self.conn is None:
            await self.connect()
    
    async def start(self):
        await self.connect()
        
        await self.execute("CREATE TABLE IF NOT EXISTS spams (type TEXT, method TEXT, channel_id INTEGER UNIQUE, guild_id INTEGER PRIMARY KEY, ments TEXT, timestamp TEXT);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_ordinary (text TEXT PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS spamtexts_nsfw (text TEXT PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS blocked_users (user_id INTEGER PRIMARY KEY, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT);")
        await self.execute("CREATE TABLE IF NOT EXISTS autopublish (channel_id INTEGER PRIMARY KEY);")
        await self.execute("CREATE TABLE IF NOT EXISTS ipou_reconstructions (number INTEGER);")
        
        for text in CONFIG.DEFAULT_ORDINARY_TEXTS:
            await self.execute("INSERT OR IGNORE INTO spamtexts_ordinary (text) VALUES (?);", text)
        for text in CONFIG.DEFAULT_NSFW_TEXTS:
            await self.execute("INSERT OR IGNORE INTO spamtexts_nsfw (text) VALUES (?);", text)
        
    async def execute(self, query: str, *args) -> str:
        await self._ensure_connection()
        
        try:
            cursor = await self.conn.execute(query, args)
            await self.conn.commit()
            return f"Executed: {cursor.rowcount} rows affected"
        except Exception as e:
            await self.conn.rollback()
            raise
    
    async def executemany(self, query: str, args_list: List[Any]) -> None:
        await self._ensure_connection()
        
        try:
            await self.conn.executemany(query, args_list)
            await self.conn.commit()
        except Exception as e:
            await self.conn.rollback()
            raise
    
    async def fetch(self, query: str, *args) -> List[Any]:
        await self._ensure_connection()
        
        cursor = await self.conn.execute(query, args)
        rows = await cursor.fetchall()
        return rows
    
    async def fetchone(self, query: str, *args) -> Optional[Any]:
        await self._ensure_connection()
        
        sqlite_query = query.replace('$1', '?').replace('$2', '?').replace('$3', '?')
        cursor = await self.conn.execute(sqlite_query, args)
        row = await cursor.fetchone()
        return row
    
    async def close(self):
        if self.conn:
            await self.conn.close()
    
    async def get_ipou_reconstruction_count(self) -> int:
        row = await self.fetchone("SELECT number FROM ipou_reconstructions ORDER BY number DESC LIMIT 1;")
        if row:
            await self.execute("UPDATE ipou_reconstructions SET number = number + 1;")
            return row['number']
        await self.execute("INSERT INTO ipou_reconstructions (number) VALUES (1);")
        return 1

db = Database()