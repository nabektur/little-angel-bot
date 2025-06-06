import sys
import logging

from modules.configuration import settings

# Логирование
stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'))
handlers = [stdout_handler]

logging.basicConfig(
    level=settings.LOGGING_LEVEL, 
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

# Discord Bot
from classes.bot import bot

from classes.database  import db
from classes.scheduler import scheduler

@bot.event
async def on_connect():
    await db.start()
    scheduler.start()
    logging.info("База данных и планировщик запущены")

@bot.event
async def on_ready():

    logging.info(f"Бот запущен как {bot.user}")

    log_channel = bot.get_channel(int(settings.CHANNEL_ID.get_secret_value()))
    if log_channel:
        await log_channel.send(f"✅ Бот запущен как **{bot.user}**")

if __name__ == '__main__':
    bot.run(
        settings.DISCORD_TOKEN.get_secret_value(), 
        log_handler=stdout_handler,
        log_formatter=logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'),
        log_level=settings.LOGGING_LEVEL
    )