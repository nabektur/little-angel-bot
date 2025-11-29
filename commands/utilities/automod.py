import io
import typing
import re
import discord
import asyncio
import unicodedata

import urllib.parse

from aiocache import SimpleMemoryCache
from cache    import AsyncLRU

from datetime    import timedelta, datetime, timezone
from discord.ext import commands

from classes.bot           import LittleAngelBot
from modules.configuration import config

hit_cache = SimpleMemoryCache()

VARIATION_SELECTOR_RE = re.compile(r"[\uFE0F]")

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2060]")

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

ENCLOSED_ALPHANUM_MAP = {
    "🄰": "a","🄱": "b","🄲": "c","🄳": "d","🄴": "e",
    "🄵": "f","🄶": "g","🄷": "h","🄸": "i","🄹": "j",
    "🄺": "k","🄻": "l","🄼": "m","🄽": "n","🄾": "o",
    "🄿": "p","🅀": "q","🅁": "r","🅂": "s","🅃": "t",
    "🅄": "u","🅅": "v","🅆": "w","🅇": "x","🅈": "y",
    "🅉": "z",

    "🅐": "a","🅑": "b","🅒": "c","🅓": "d","🅔": "e",
    "🅕": "f","🅖": "g","🅗": "h","🅘": "i","🅙": "j",
    "🅚": "k","🅛": "l","🅜": "m","🅝": "n","🅞": "o",
    "🅟": "p","🅠": "q","🅡": "r","🅢": "s","🅣": "t",
    "🅤": "u","🅥": "v","🅦": "w","🅧": "x","🅨": "y",
    "🅩": "z",

    "🆊": "j","🆋": "k","🆌": "l","🆍": "m","🆎": "ab",
    "🆏": "k","🆐": "p","🆑": "cl","🆒": "cool",
    "🆓": "free","🆔": "id","🆕": "new","🆖": "ng",
    "🆗": "ok","🆘": "sos","🆙": "up",
    "🆚": "vs","🆛": "b","🆜": "m","🆝": "n",
    "🆞": "o","🆟": "p","🆠": "q","🆡": "p",
    "🆢": "s","🆣": "t","🆤": "u","🆥": "v",
    "🆦": "w","🆧": "x","🆨": "h","🆩": "i",
    "🆪": "j","🆫": "k","🆬": "l","🆭": "m",
    "🆮": "n","🆯": "o",
}

FANCY_MAP = {
    **{chr(i): chr(i - 0xFEE0).lower() for i in range(0xFF21, 0xFF3B)},
    **{chr(i): chr(i - 0xFEE0).lower() for i in range(0xFF41, 0xFF5B)},

    **{chr(0x1D400 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D41A + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D434 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D44E + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D468 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D482 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D49C + i): chr(ord('a') + i) for i in range(26) if i not in [1,4,7,11,12,17,18]},
    **{chr(0x1D4B6 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D4D0 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D4EA + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D504 + i): chr(ord('a') + i) for i in range(26) if i not in [1,4,18,23]},
    **{chr(0x1D51E + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D538 + i): chr(ord('a') + i) for i in range(26) if i not in [1,4,17]},
    **{chr(0x1D552 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D5A0 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D5BA + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D5D4 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D5EE + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D608 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D622 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D63C + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D656 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1D670 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x1D68A + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x24B6 + i): chr(ord('a') + i) for i in range(26)},
    **{chr(0x24D0 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1F150 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1F130 + i): chr(ord('a') + i) for i in range(26)},

    **{chr(0x1F170 + i): chr(ord('a') + i) for i in range(26)},
}

_COMBINED_MAP = {}
_COMBINED_MAP.update(EMOJI_ASCII_MAP)
_COMBINED_MAP.update(REGIONAL_INDICATOR_MAP)
_COMBINED_MAP.update(ENCLOSED_ALPHANUM_MAP)
# HOMOGLYPHS - у нас маппинг кириллицы->латиницы, добавляем напрямую
_COMBINED_MAP.update(HOMOGLYPHS)
_COMBINED_MAP.update(FANCY_MAP)

async def _char_to_ascii(ch: str) -> str:

    if VARIATION_SELECTOR_RE.match(ch):
        return ""

    if ZERO_WIDTH_RE.match(ch):
        return ""

    if ch in _COMBINED_MAP:
        return _COMBINED_MAP[ch]

    code = ord(ch)

    if 0x1F1E6 <= code <= 0x1F1FF:
        return chr(ord("a") + (code - 0x1F1E6))

    decomp = unicodedata.normalize("NFKD", ch)
    if decomp:
        base = decomp[0]
        if ('A' <= base <= 'Z') or ('a' <= base <= 'z'):
            return base.lower()

    if ch.isdigit():
        return ch

    if ch in " \t\r\n./\\|_•·-:":
        return " "

    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = ""

    if name:
        nm = name.upper().split()
        # одиночная буква где-то внутри имени
        for token in nm:
            if len(token) == 1 and 'A' <= token <= 'Z':
                return token.lower()

    return " "
    

async def normalize_and_compact(raw_text: str) -> str:

    try:
        text = urllib.parse.unquote(raw_text)
    except Exception:
        text = raw_text


    text = unicodedata.normalize("NFKC", text)

    out = []
    for ch in text:
        out.append(await _char_to_ascii(ch))

    collapsed = "".join(out)
    collapsed = re.sub(r"\s+", " ", collapsed).strip()
    compact = re.sub(r"[^a-z0-9]", "", collapsed.lower())
    return compact

@AsyncLRU(maxsize=5000)
async def detect_links(raw_text: str):

    # функция нормализации
    compact = await normalize_and_compact(raw_text)

    # --- Discord ---
    if "discordgg" in compact or "discordcom" in compact or "discordappcom" in compact:
        return "discord.gg" if "discordgg" in compact else "discord.com" if "discordcom" in compact else "discordapp.com"
    # --- Telegram ---
    if "tme" in compact or "telegramme" in compact or "telegramorg" in compact:
        return "t.me" if "tme" in compact else "telegram.me" if "telegramme" in compact else "telegram.org"

    return None


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
        
        # расстановка приоритетов
        priority: int = 1

        if message.channel.permissions_for(message.author).manage_messages:
            priority = 0
        elif message.channel.id in config.ADS_CHANNELS_IDS:
            priority = 0

        # модерация активности

        if message.activity is not None:

            # условия срабатывания
            if priority > 0:

                if not await hit_cache.get(message.author.id):
                    await hit_cache.set(message.author.id, 0, ttl=3600)

                hit_data: int = await hit_cache.get(message.author.id)
                await hit_cache.set(message.author.id, hit_data + 1, ttl=3600)
                hit_data = await hit_cache.get(message.author.id)

                activity_info = (
                    f"Тип: {message.activity.get('type')}\n"
                    f"Party ID: {message.activity.get('party_id')}\n"
                )

                if hit_data <= 2:
                    log_embed_description = (
                        f"Удалено сообщение от участника {message.author.mention} (`@{message.author}`)\n"
                        f"Причина: подозрение на рекламу через активность\n\n"
                        f"Информация об активности:\n```\n{activity_info}```"
                    )
                else:
                    log_embed_description = (
                        f"Участнику {message.author.mention} (`@{message.author}`) был выдан мут на 1 час\n"
                        f"Причина: реклама через активность.\n\n"
                        f"Информация об активности:\n```\n{activity_info}```"
                    )

                log_embed = discord.Embed(
                    title="Реклама через активность",
                    description=log_embed_description,
                    color=0xff0000
                )
                log_embed.set_footer(text=f"ID: {message.author.id}")
                log_embed.set_thumbnail(url=message.author.display_avatar.url)
                log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                log_embed.add_field(name="Канал:", value=f"{message.channel.mention} (`#{message.channel.name}`)", inline=False)

                await self.safe_send_to_log(embed=log_embed)

                if hit_data <= 2:
                    mention_embed_description = (
                        f"На сервере запрещена реклама сторонних серверов (даже внутри активностей)\n"
                        f"Наказание не применяется, за исключением удаления сообщения\n\n"
                        f"Информация об активности:\n```\n{activity_info}```\n\n"
                        f"-# Дополнительную информацию можно посмотреть в канале автомодерации\n\n"
                    )
                else:
                    mention_embed_description = (
                        f"На сервере запрещена реклама сторонних серверов (даже внутри активностей)\n"
                        f"Тебе выдан мут на 1 час\n\n"
                        f"Информация об активности:\n```\n{activity_info}```\n\n"
                        f"-# Дополнительную информацию можно посмотреть в канале автомодерации\n\n"
                    )

                mention_embed = discord.Embed(
                    title="Реклама внутри активности",
                    description=mention_embed_description,
                    color=0xff0000
                )
                mention_embed.set_thumbnail(url=message.author.display_avatar.url)
                mention_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                mention_embed.set_footer(text="Если ты считаешь, что это ошибка, проигнорируй это сообщение" if hit_data <=2 else "Если ты считаешь, что это ошибка, обратись к модераторам")

                await self.safe_send_to_channel(message.channel, content=message.author.mention, embed=mention_embed)

                await self.safe_delete(message)

                if hit_data > 2:
                    await self.safe_timeout(message.author, timedelta(hours=1), "Реклама через активность")
                    await hit_cache.delete(message.author.id)

                return
                
        
        # модерация сообщений
        if message.content:
                
                if priority > 0:

                    matched = await detect_links(message.content)

                    if matched:

                        if not await hit_cache.get(message.author.id):
                            await hit_cache.set(message.author.id, 0, ttl=3600)

                        hit_data: int = await hit_cache.get(message.author.id)
                        await hit_cache.set(message.author.id, hit_data + 1, ttl=3600)
                        hit_data = await hit_cache.get(message.author.id)

                        # первые 300 символов сообщения
                        preview = message.content[:300].replace("`", "'")

                        if hit_data <= 2:
                            log_embed_description = (
                                f"Удалено сообщение от участника {message.author.mention} (`@{message.author}`)\n"
                                f"Причина: подозрение на рекламу в сообщении\n\n"
                                f"Совпадение:\n```\n{matched}\n```\n"
                                f"Первые 300 символов:\n```\n{preview}\n```"
                            )
                        else:
                            log_embed_description = (
                                f"Участнику {message.author.mention} (`@{message.author}`) был выдан мут на 1 час\n"
                                f"Причина: реклама в сообщении.\n\n"
                                f"Совпадение:\n```\n{matched}\n```\n"
                                f"Первые 300 символов:\n```\n{preview}\n```"
                            )

                        log_embed = discord.Embed(
                            title="Реклама в сообщении",
                            description=log_embed_description,
                            color=0xff0000
                        )

                        log_embed.set_footer(text=f"ID: {message.author.id}")
                        log_embed.set_thumbnail(url=message.author.display_avatar.url)
                        log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                        log_embed.add_field(name="Канал:", value=f"{message.channel.mention} (`#{message.channel.name}`)", inline=False)

                        await self.safe_send_to_log(embed=log_embed)

                        if hit_data <= 2:
                            mention_embed_description = (
                                f"На сервере запрещена реклама сторонних серверов\n"
                                f"Наказание не применяется, за исключением удаления сообщения\n\n"
                                f"Совпадение, на которое отреагировал бот:\n```\n{matched}\n```\n\n"
                                f"-# Дополнительную информацию можно посмотреть в канале автомодерации"
                            )
                        else:
                            mention_embed_description = (
                                f"На сервере запрещена реклама сторонних серверов\n"
                                f"Тебе выдан мут на 1 час\n\n"
                                f"Совпадение, на которое отреагировал бот:\n```\n{matched}\n```\n\n"
                                f"-# Дополнительную информацию можно посмотреть в канале автомодерации"
                            )

                        mention_embed = discord.Embed(
                            title="Реклама в сообщении",
                            description=mention_embed_description,
                            color=0xff0000
                        )
                        mention_embed.set_thumbnail(url=message.author.display_avatar.url)
                        mention_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                        mention_embed.set_footer(text="Если ты считаешь, что это ошибка, проигнорируй это сообщение" if hit_data <=2 else "Если ты считаешь, что это ошибка, обратись к модераторам")
                        
                        await self.safe_send_to_channel(message.channel, content=message.author.mention, embed=mention_embed)

                        await self.safe_delete(message)

                        if hit_data > 2:
                            await self.safe_timeout(message.author, timedelta(hours=1), "Реклама в сообщении")
                            await hit_cache.delete(message.author.id)

                        return

        # модерация вложенных файлов

        if message.attachments and priority > 0:

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

                matched = await detect_links(content)

                if matched:

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
                            f"Участнику {message.author.mention} (`@{message.author}`) был выдан мут на 1 час\n"
                            f"Причина: реклама внутри прикрепленного файла.\n\n"
                            f"Совпадение:\n```\n{matched}\n```\n"
                            f"Информация о файле:\n```\n{file_info}```\n"
                            f"Первые 300 символов:\n```\n{preview}\n```"
                        ),
                        color=0xff0000
                    )

                    log_embed.set_footer(text=f"ID: {message.author.id}")
                    log_embed.set_thumbnail(url=message.author.display_avatar.url)
                    log_embed.set_author(name=message.guild.name, icon_url=message.guild.icon.url if message.guild.icon else None)
                    log_embed.add_field(name="Канал:", value=f"{message.channel.mention} (`#{message.channel.name}`)", inline=False)

                    await self.safe_send_to_log(embed=log_embed)

                    mention_embed = discord.Embed(
                        title="Реклама внутри файла",
                        description=(
                            f"На сервере запрещена реклама сторонних серверов (даже внутри файлов)\n"
                            f"Тебе выдан мут на 1 час\n\n"
                            f"Совпадение, на которое отреагировал бот:\n```\n{matched}\n```\n"
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