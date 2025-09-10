import sys
import asyncio
import logging
import discord
import traceback

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

    chan = bot.get_channel(1415362186607591508)

    msg = await chan.fetch_message(1415373182881497158)

    embed = discord.Embed(title="<a:black_melting_heart:1410351745170935959> Умничка", description="А теперь нажми на реакцию галочки ниже для завершения верификации", color=0x5b00c1)

    await msg.edit(content="@everyone", embed=embed)

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
