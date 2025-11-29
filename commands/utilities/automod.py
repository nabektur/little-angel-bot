import io
import typing
import re
import discord
import asyncio
import unicodedata

from rapidfuzz import fuzz

from datetime import timedelta, datetime, timezone
from discord.ext import commands

from cache import AsyncLRU
from classes.bot import LittleAngelBot
from modules.configuration import config

# emoji-букв -> ASCII
EMOJI_ASCII_MAP = {
    "🅰️": "a", "🅱️": "b", "🅾️": "o", "🅿️": "p",
    "Ⓜ️": "m", "ℹ️": "i", "❌": "x", "⭕": "o",
}

# 🇦 -> a
REGIONAL_INDICATOR_MAP = {
    chr(code): chr(ord('a') + (code - 0x1F1E6))
    for code in range(0x1F1E6, 0x1F1FF + 1)
}

# Кириллица -> латиница
HOMOGLYPHS = {
    "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "х": "x", "у": "y", "к": "k",
    "м": "m", "т": "t", "в": "b", "н": "h",
    "д": "d", "г": "g", "б": "b",
}

async def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)

    out = []

    for ch in text:

        # региональные буквы 🇦🇧
        if ch in REGIONAL_INDICATOR_MAP:
            out.append(REGIONAL_INDICATOR_MAP[ch])
            continue

        # emoji-буквы 🅳🅾️🅶
        if ch in EMOJI_ASCII_MAP:
            out.append(EMOJI_ASCII_MAP[ch])
            continue

        # кириллица -> латиница
        if ch.lower() in HOMOGLYPHS:
            out.append(HOMOGLYPHS[ch.lower()])
            continue

        # NFKD мат. символы Q𝕠𝖗𝖉
        decomp = unicodedata.normalize("NFKD", ch)
        if decomp and 'a' <= decomp[0].lower() <= 'z':
            out.append(decomp[0].lower())
            continue

        # цифры
        if ch.isdigit():
            out.append(ch)
            continue

        # всё остальное -> пробел
        out.append(" ")

    normalized = "".join(out)

    # убрать повторные пробелы
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()

async def clean_text(text: str):
    text = text.lower()
    text = re.sub(r"[\s\.\|\•\·\_]+", "", text)
    text = re.sub(r"[^a-z0-9]", "", text)
    return text

DISCORD_PATTERNS = [
    re.compile(r"discordgg([a-z0-9]{2,32})"),
    re.compile(r"discordcominvite([a-z0-9]{2,32})"),
    re.compile(r"discordappcominvite([a-z0-9]{2,32})"),
]

TELEGRAM_PATTERNS = [
    re.compile(r"tme([a-z0-9_/]{2,64})"),
    re.compile(r"telegramme([a-z0-9_/]{2,64})"),
    re.compile(r"telegramorg([a-z0-9_/]{2,64})"),
]

@AsyncLRU(maxsize=5000)
async def detect_links(raw_text: str):
    text = await normalize_text(raw_text)
    cleaned = await clean_text(text)

    # Discord
    for rgx in DISCORD_PATTERNS:
        m = rgx.search(cleaned)
        if m:
            return ("discord", m.group(1))

    # Telegram
    for rgx in TELEGRAM_PATTERNS:
        m = rgx.search(cleaned)
        if m:
            return ("telegram", m.group(1))

    return None, None


class AutoModeration(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    async def safe_send_to_channel(self, channel: discord.abc.Messageable, *args, **kwargs):
        try:
            return await channel.send(*args, **kwargs)
        except Exception:
            return None

    async def safe_send_to_log(self, *args, **kwargs):
        try:
            channel = self.bot.get_channel(int(config.AUTOMOD_LOGS_CHANNEL_ID.get_secret_value()))
            if not channel:
                channel = await self.bot.fetch_channel(int(config.AUTOMOD_LOGS_CHANNEL_ID.get_secret_value()))
            return await channel.send(*args, **kwargs)
        except Exception:
            return None

    async def safe_delete(self, msg: discord.Message):
        try: 
            await msg.delete()
        except Exception:
            pass

    async def safe_timeout(self, member: discord.Member, duration: timedelta, reason: str):
        try:
            await member.timeout(duration, reason=reason)
        except Exception:
            pass


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # базовые проверки
        if message.author == self.bot.user:
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.guild.id != int(config.GUILD_ID.get_secret_value()):
            return
        
        #расстановка приоритетов
        priority: typing.Literal["full", "high", "low", "none"] = "full"

        # модерация активности

        if message.activity is not None:

            # условия срабатывания
            if priority in ["full", "high"]:

                activity_info = (
                    f"Тип: {message.activity.type}\n"
                    f"Party ID: {message.activity.party_id}\n"
                )

                log_embed = discord.Embed(
                    title="Реклама через активность",
                    description=(
                        f"Удалено сообщение от участника {message.author.mention} (`@{message.author}`)\n"
                        f"Причина: подозрение на рекламу через активность\n\n"
                        f"Информация об активности:\n```\n{activity_info}```"
                    ),
                    color=0xff0000
                )
                log_embed.set_footer(text=f"ID: {message.author.id}")
                log_embed.set_thumbnail(url=message.author.display_avatar.url)
                log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                log_embed.add_field(name="Канал:", value=f"{message.channel.mention}", inline=False)

                await self.safe_send_to_log(embed=log_embed)

                mention_embed = discord.Embed(
                    title="Реклама внутри активности",
                    description=(
                        f"На сервере запрещена реклама сторонних серверов (даже внутри активностей)\n"
                        f"Наказание не применяется, за исключением удаления сообщения\n\n"
                        f"Информация об активности:\n```\n{activity_info}```\n\n"
                        f"-# Дополнительную информацию можно посмотреть в канале автомодерации\n\n"
                    ),
                    color=0xff0000
                )
                mention_embed.set_thumbnail(url=message.author.display_avatar.url)
                mention_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                mention_embed.set_footer(text="Если ты считаешь, что это ошибка, проигнорируй это сообщение")

                await self.safe_send_to_channel(message.channel, content=message.author.mention, embed=mention_embed)

                await self.safe_delete(message)
                return
                
        
        # модерация сообщений
        if message.content and priority in ["full"]:

                matched_platform, matched = await detect_links(message.content)

                if matched_platform and matched:

                    # первые 300 символов сообщения
                    preview = message.content[:300].replace("`", "'")

                    log_embed = discord.Embed(
                        title="Реклама в сообщении",
                        description=(
                            f"Удалено сообщение от участника {message.author.mention} (`@{message.author}`)\n"
                            f"Причина: подозрение на рекламу в сообщении\n\n"
                            f"Совпадение:\n```\n{matched} | {matched_platform}\n```\n"
                            f"Первые 300 символов:\n```\n{preview}\n```"
                        ),
                        color=0xff0000
                    )

                    log_embed.set_footer(text=f"ID: {message.author.id}")
                    log_embed.set_thumbnail(url=message.author.display_avatar.url)
                    log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                    log_embed.add_field(name="Канал:", value=message.channel.mention, inline=False)

                    await self.safe_send_to_log(embed=log_embed)

                    mention_embed = discord.Embed(
                        title="Реклама в сообщении",
                        description=(
                            f"На сервере запрещена реклама сторонних серверов\n"
                            f"Наказание не применяется, за исключением удаления сообщения\n\n"
                            f"Совпадение, на которое отреагировал бот:\n```\n{matched} | {matched_platform}\n```\n\n"
                            f"-# Дополнительную информацию можно посмотреть в канале автомодерации"
                        ),
                        color=0xff0000
                    )
                    mention_embed.set_thumbnail(url=message.author.display_avatar.url)
                    mention_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                    mention_embed.set_footer(text="Если ты считаешь, что это ошибка, проигнорируй это сообщение")

                    await self.safe_send_to_channel(message.channel, content=message.author.mention, embed=mention_embed)

                    await self.safe_delete(message)
                    return

        # модерация вложенных файлов

        if message.attachments and priority in ["full", "high", "low"]:

            for attachment in message.attachments:

                if not attachment.content_type:
                    continue

                if not any(ct in attachment.content_type for ct in ["text", "json", "xml", "csv", "html", "htm", "md", "yaml", "yml", "ini", "log", "multipart", "text/plain", "text/html", "text/markdown", "text/xml", "text/csv", "text/yaml", "text/yml", "text/ini", "text/log"]):
                    continue

                # ограничение по размеру
                # if attachment.size > MAX_FILE_SIZE_BYTES:
                #     continue

                try:
                    file_bytes = await asyncio.wait_for(attachment.read(), timeout=30)
                except (asyncio.TimeoutError, discord.HTTPException):
                    continue

                if file_bytes.count(b"\x00") > 100:
                    continue  # бинарный файл

                content = file_bytes[:1_000_000].decode(errors='ignore')

                matched_platform, matched = await detect_links(content)

                if matched_platform and matched:

                    # первые 300 символов файла
                    preview = content[:300].replace("`", "'")

                    file_info = (
                        f"Имя файла: {attachment.filename}\n"
                        f"Размер: {attachment.size} байт\n"
                        f"Тип: {attachment.content_type}\n"
                    )

                    log_embed = discord.Embed(
                        title="Реклама внутри файла",
                        description=(
                            f"Участнику {message.author.mention} (`@{message.author}`) был выдан мут на 1 час.\n"
                            f"Причина: реклама внутри прикрепленного файла.\n\n"
                            f"Совпадение:\n```\n{matched} | {matched_platform}\n```\n"
                            f"Информация о файле:\n```\n{file_info}```\n"
                            f"Первые 300 символов:\n```\n{preview}\n```"
                        ),
                        color=0xff0000
                    )

                    log_embed.set_footer(text=f"ID: {message.author.id}")
                    log_embed.set_thumbnail(url=message.author.display_avatar.url)
                    log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                    log_embed.add_field(name="Канал:", value=message.channel.mention, inline=False)

                    await self.safe_send_to_log(embed=log_embed)

                    mention_embed = discord.Embed(
                        title="Реклама внутри файла",
                        description=(
                            f"На сервере запрещена реклама сторонних серверов (даже внутри файлов)\n"
                            f"Тебе выдан мут на 1 час\n\n"
                            f"Совпадение, на которое отреагировал бот:\n```\n{matched} | {matched_platform}\n```\n"
                            f"Информация о файле:\n```\n{file_info}```\n\n"
                            f"-# Дополнительную информацию можно посмотреть в канале автомодерации"
                        ),
                        color=0xff0000
                    )
                    mention_embed.set_thumbnail(url=message.author.display_avatar.url)
                    mention_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)

                    await self.safe_send_to_channel(message.channel, content=message.author.mention, embed=mention_embed)

                    await self.safe_delete(message)
                    await self.safe_timeout(message.author, timedelta(hours=1), "Реклама в текстовом файле")
                    return


async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoModeration(bot))