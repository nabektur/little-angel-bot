import io
import typing
import discord
import asyncio

from rapidfuzz import fuzz

from datetime                  import timedelta, datetime, timezone
from apscheduler.triggers.date import DateTrigger

from cache import AsyncLRU, AsyncTTL

from discord     import app_commands
from discord.ext import commands

from classes.bot       import LittleAngelBot
from classes.database  import db

from modules.configuration  import config

links_patterns = [
    "discord.gg",
    "discord.com/invite",
    "discordapp.com/invite",
    "t.me/joinchat",
    "t.me",
    "https://discord.gg",
    "https://discord.com/invite",
    "https://discordapp.com/invite",
    "https://t.me/joinchat",
    "https://t.me"
]

@AsyncLRU(maxsize=1024)
async def find_spam_matches(text: str, patterns: typing.List[str] = None) -> bool:
    if not text:
        return False
    
    if patterns is None:
        patterns = links_patterns

    text = text.lower()

    for p in patterns:
        if p in text:
            return True

    words = text.replace("/", " ").replace("\\", " ").replace("-", " ").split()

    for w in words:
        for p in patterns:
            if fuzz.ratio(w, p) > 80:
                return True

    return False

class AutoModeration(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if not message.guild:
            return
        if message.guild.id != int(config.GUILD_ID.get_secret_value()):
            return
        if message.activity != None:
            await message.delete()
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and ("multipart" in attachment.content_type or "text" in attachment.content_type):
                    try: 
                        file_bytes = await attachment.read()
                    except: 
                        return
                    else:
                        content = file_bytes.decode(errors='ignore')
                        if await find_spam_matches(content):
                            await message.delete()
                            await message.author.timeout(timedelta(hours=1), "Приглашения в текстовом файле.")
                            return


async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoModeration(bot))
