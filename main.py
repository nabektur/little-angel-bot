import os
import dotenv

# Loading .env
dotenv.load_dotenv()

# Discord Bot
from classes.bot import bot

@bot.event
async def on_ready():
    
    from modules.database import start_db
    await start_db()

    print(f"Бот запущен как {bot.user}")

    log_channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if log_channel:
        await log_channel.send(f"✅ Бот запущен как **{bot.user}**")


bot.run(os.getenv("DISCORD_TOKEN"))