import asyncio
import logging
import sys
import traceback

import discord

from classes.bot import bot  # Кастомный класс бота
from modules.configuration import CONFIG

LOGGER = logging.getLogger(__name__)

if sys.platform == "win32": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@bot.event
async def on_ready():
    LOGGER.info(f"Бот запущен как {bot.user}")

    if len(bot.guilds) > 1:
        await asyncio.gather(*[
            guild.leave() for guild in bot.guilds 
            if guild.id != CONFIG.GUILD_ID
        ])

    log_channel = bot.get_channel(CONFIG.BOT_LOGS_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=discord.Embed(description=f"☑️ Бот запущен как **{bot.user}**", color=CONFIG.LITTLE_ANGEL_COLOR))

def main():
    try:
        bot.run(CONFIG.DISCORD_TOKEN.get_secret_value())
    except Exception as e:
        LOGGER.error(f"Произошла ошибка {e}:\n{traceback.format_exc()}")
    finally:
        if bot.is_closed() is False:
            asyncio.run(asyncio.to_thread(bot.close))
            
        LOGGER.info("Бот остановлен")

    sys.exit(0)

if __name__ == '__main__':
    main()  # Запуск бота
