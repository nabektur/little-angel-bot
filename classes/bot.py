import sys
import signal
import asyncio
import logging
import discord

from discord.ext import commands

from modules.configuration import config

from classes.database  import db
from classes.scheduler import scheduler

_log = logging.getLogger(__name__)

class LittleAngelBot(commands.AutoShardedBot):

    def __init__(self):
        discord_intents = discord.Intents.default()
        discord_intents.message_content = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(config.BOT_PREFIX),
            case_insensitive=True,
            help_command=None,
            intents=discord_intents,
            status=discord.Status.idle,
            activity=discord.Streaming(
                name=config.ACTIVITY_NAME,
                url=config.STREAMING_URL
            )
        )

    async def setup_hook(self):
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.close()))

        from modules.extension_loader import load_all_extensions
        from modules.spam_runner      import sync_spam_from_database

        await db.start()
        await sync_spam_from_database(bot)
        scheduler.start()
        _log.info("База данных и планировщик запущены")

        await load_all_extensions(self)
        await load_all_extensions(self, "listeners")

    async def close(self):
        await db.close()
        scheduler.shutdown(wait=True)

        _log.info("База данных и планировщик остановлены")

        await super().close()

bot = LittleAngelBot()