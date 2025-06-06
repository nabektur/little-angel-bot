import os
import discord
import dotenv

# Loading .env
dotenv.load_dotenv()

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True

from modules.bot_class import LittleAngelBot

bot = LittleAngelBot(
    command_prefix="$",
    intents=intents,
    activity=discord.Streaming(
        name="ДЕПНУЛ НЕЙМАРА ЗА $500,000!",
        url="https://www.twitch.tv/jasteeq"
    )
)

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")
    log_channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if log_channel:
        await log_channel.send(f"✅ Бот запущен как **{bot.user}**")


bot.run(os.getenv("DISCORD_TOKEN"))