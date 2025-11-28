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
async def find_spam_matches(text: str, patterns: typing.List[str] = None) -> typing.Union[bool, str]:
    if not text:
        return False
    
    if patterns is None:
        patterns = links_patterns

    text = text.lower()

    for p in patterns:
        if p in text:
            return p

    words = text.replace("/", " ").replace("\\", " ").replace("-", " ").split()

    for w in words:
        for p in patterns:
            if fuzz.ratio(w, p) > 80:
                return w

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
                        matched = await find_spam_matches(content)
                        if matched:
                            log_channel = await self.bot.fetch_channel(int(config.AUTOMOD_LOGS_CHANNEL_ID.get_secret_value()))
                            embed = discord.Embed(
                                title="Реклама внутри файлов",
                                description=f"Участнику {message.author.mention} (`{message.author}`) был выдан мут на 1 час за рекламу в текстовом файле\n\nЧасть текста, на которую среагировал бот:```\n{matched}```",
                                color=0xff0000
                            )
                            embed.set_footer(text=f"ID: {message.author.id}")
                            embed.add_field(name="Канал:", value=f"{message.channel.mention} (`#{message.channel}`)", inline=False)
                            await log_channel.send(embed=embed)
                            await message.delete()
                            await message.author.timeout(until=timedelta(hours=1), reason="Реклама в текстовом файле.")
                            return


async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoModeration(bot))
