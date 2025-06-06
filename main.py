import os
import discord
import dotenv

from discord.ext import commands
from discord import app_commands

# Loading .env
dotenv.load_dotenv()

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True

class LittleAngelBot(commands.AutoShardedBot):
    async def setup_hook(self):
        from modules.extension_loader import load_all_extensions

        await load_all_extensions(self)

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