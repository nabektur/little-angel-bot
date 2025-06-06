import asyncio

# Discord Bot
from classes.bot import bot

from classes.database import db
from classes.scheduler import scheduler
from modules.configuration import settings

@bot.event
async def on_connect():
    asyncio.set_event_loop(asyncio.get_event_loop())
    scheduler.start()
    await db.start()

@bot.event
async def on_ready():

    print(f"Бот запущен как {bot.user}")

    log_channel = bot.get_channel(int(settings.CHANNEL_ID.get_secret_value()))
    if log_channel:
        await log_channel.send(f"✅ Бот запущен как **{bot.user}**")

if __name__ == '__main__':
    bot.run(settings.DISCORD_TOKEN.get_secret_value(), log_level=settings.LOGGING_LEVEL)