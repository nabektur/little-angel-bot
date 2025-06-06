import os
import asyncpg
import asyncio
import logging

from typing import Literal, Union

DATABASE_URL = os.getenv("DATABASE_URL")

async def execute(query: str, result_format: Literal['fetchall', 'fetchone'] = None, args: tuple = tuple()) -> Union[list, tuple]:
    con = await asyncpg.connect(DATABASE_URL)
    result = await con.execute(query, *args)
    await con.close()
    return result

async def executemany(query: str, result_format: Literal['fetchall', 'fetchone'] = None, args: tuple = tuple()) -> None:
    con = await asyncpg.connect(DATABASE_URL)
    result = await con.executemany(query, *args)
    await con.close()
    return result

async def start_db():
    ...
    # await execute("CREATE TABLE IF NOT EXISTS last_responses (dialog_id varchar PRIMARY KEY, last_response_id varchar);")
    # await execute("CREATE TABLE IF NOT EXISTS users_carts (dialog_id varchar PRIMARY KEY, cart varchar);")
    # await execute("CREATE TABLE IF NOT EXISTS users_orders (number integer PRIMARY KEY, dialog_id varchar, address varchar, delivery_time_start varchar, delivery_time_end varchar, additional_comments varchar, cart varchar);")