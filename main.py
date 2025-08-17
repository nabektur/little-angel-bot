import sys
import asyncio
import logging
import discord
import traceback

from modules.keep_alive import keep_alive

keep_alive()

from modules.configuration import config

_log = logging.getLogger(__name__)

if sys.platform == "win32": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Discord Bot
from classes.bot import bot

@bot.event
async def on_ready():
    _log.info(f"Бот запущен как {bot.user}")

    log_channel = bot.get_channel(int(config.BOT_LOGS_CHANNEL_ID.get_secret_value()))
    if log_channel:
        await log_channel.send(embed=discord.Embed(description=f"☑️ Бот запущен как **{bot.user}**", color=config.LITTLE_ANGEL_COLOR))

def main():
    try:
        bot.run(config.DISCORD_TOKEN.get_secret_value())
    except Exception as e:
        _log.error(f"Произошла ошибка {e}:\n{traceback.format_exc()}")
    finally:
        if bot.is_closed() is False:
            asyncio.run(asyncio.to_thread(bot.close))
            
        _log.info("Бот остановлен")

if __name__ == '__main__':
    # Запуск
    main()
