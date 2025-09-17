import sys
import signal
import asyncio
import logging
import discord

from discord.ext import commands, tasks

from modules.configuration import config

from classes.database  import db
from classes.scheduler import scheduler

_log = logging.getLogger(__name__)

class LittleAngelBot(commands.AutoShardedBot):

    def __init__(self):
        discord_intents = discord.Intents.default()
        discord_intents.message_content = True
        discord_intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(config.BOT_PREFIX),
            case_insensitive=True,
            help_command=None,
            intents=discord_intents,
            # status=discord.Status.idle,
        )

    async def setup_hook(self):
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda _sig=sig: asyncio.create_task(self.close()))

        from modules.keep_alive import keep_alive

        keep_alive()

        from modules.extension_loader import load_all_extensions
        from modules.spam_runner      import sync_spam_from_database

        await db.start()
        await sync_spam_from_database(self)
        scheduler.start()
        _log.info("База данных и планировщик запущены")

        change_status_periodically.start()

        await load_all_extensions(self)
        await load_all_extensions(self, "listeners")

    async def close(self):
        await db.close()
        await asyncio.to_thread(scheduler.shutdown, wait=True)

        _log.info("База данных и планировщик остановлены")

        await super().close()

bot = LittleAngelBot()

@tasks.loop(seconds=5)
async def change_status_periodically():
    next_status = next(config.ACTIVITY_NAMES)
    await bot.change_presence(
        status=discord.Status.idle, activity=discord.Streaming(name=next_status.get("name"), url=next_status.get("streaming_url")) if next_status.get("streaming_url") else discord.CustomActivity(name=next_status.get("name"))
    )