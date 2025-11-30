import io
import typing
import re
import discord
import asyncio
import unicodedata

import urllib.parse

from aiocache  import SimpleMemoryCache
from cache     import AsyncLRU
from rapidfuzz import fuzz, process

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

async def looks_like_discord(word: str, threshold=70):
    if len(word) < 5:
        return False
    score = fuzz.partial_ratio("discord", word)
    return score >= threshold

def extract_possible_domains(text: str):
    text = text.replace(" ", "")
    candidates = []

    dom1 = re.findall(r"([a-zA-Z0-9]+)\.([a-zA-Z]{2,4})", text)
    for a, b in dom1:
        candidates.append(a + "." + b)

    dom2 = re.findall(r"([a-zA-Z0-9]+)(gg|com|app)", text)
    for a, b in dom2:
        candidates.append(a + b)

    return candidates

@AsyncLRU(maxsize=5000)
async def detect_links(raw_text: str):

    # функция нормализации
    compact = await normalize_and_compact(raw_text)

    # --- Discord ---

    if "discordgg" in compact or "discordcom" in compact or "discordappcom" in compact:
        if "discordgg" in compact:
            return "discord.gg"
        if "discordcom" in compact:
            return "discord.com"
        if "discordappcom" in compact:
            if not (any(x in raw_text for x in ["https://cdn.discordapp.com", "https://media.discordapp.net", "https://images-ext-1.discordapp.net"])):
                return "discordapp.com"
            elif "invite" in compact:
                return "discordapp.com"

    
    # --- Telegram ---

    if "telegramme" in compact or "telegramorg" in compact:
        return "telegram.me" if "telegramme" in compact else "telegram.org"
    if "t.me" in raw_text.replace(" ", "").lower():
        return "t.me"
    if re.search(r"(telegram\.me|telegram\.org)", raw_text.replace(" ", "").lower()):
        m = re.search(r"(telegram\.me|telegram\.org)", raw_text.replace(" ", "").lower())
        return m.group(1)
    
    # --- доменные структуры ---
    candidates = extract_possible_domains(compact)

    for cand in candidates:

        # отделяем левую часть домена
        left = cand.split(".")[0].replace("gg","").replace("com","").replace("app","")

        # проверяем, похожа ли левая часть на discord
        if await looks_like_discord(left):

            # игнорируем слово discord (не ссылка)
            if left == "discord":
                continue

            if any(x in cand for x in ["imagesext1discordapp", "mediadiscordapp", "cdndiscordapp"]):
                if not "invite" in compact:
                    continue  # это не ссылка-приглашение

            # ловим только ссылки
            return f"Похоже на ссылку приглашения в Discord сервер ({cand})"

    return None

EMPTY_SPAM_LINE_RE = re.compile(r"^[\s\`\u200B-\u200F\uFEFF]{0,}$")

async def is_spam_block(message: str) -> bool:
    """
    пустые строки, код-блоки, мусорные символы.
    """

    # слишком много строк
    lines = message.split("\n")
    if len(lines) >= 40:
        empty_like = sum(1 for l in lines if EMPTY_SPAM_LINE_RE.match(l))
        if empty_like / len(lines) >= 0.7:
            return True

    # код-блок
    if message.count("```") >= 2:
        inner = message.split("```")
        if len(inner) >= 3:
            code = inner[1]
            if len(code) > 1500 or code.count("\n") > 25:
                return True

    # содержит более 3000 символов
    if len(message) > 3000:
        compact = re.sub(r"[a-zA-Z0-9а-яА-ЯёЁ]+", "", message)
        if len(compact) / len(message) >= 0.7:
            return True

    # много повторяющихся символов
    if re.search(r"(.)\1{40,}", message):
        return True

    # много zero-width / невидимых символов
    inv = re.findall(ZERO_WIDTH_RE, message)
    if len(inv) > 50:
        return True

    return False


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
            channel: discord.TextChannel = self.bot.get_channel(config.AUTOMOD_LOGS_CHANNEL_ID)
            if not channel:
                channel: discord.TextChannel = await self.bot.fetch_channel(config.AUTOMOD_LOGS_CHANNEL_ID)
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

    async def handle_violation(
        self,
        message: discord.Message,
        reason_title: str,
        reason_text: str,
        extra_info: str = "",
        timeout_reason: str = None,
        force_harsh: bool = False,
    ):
        user = message.author
        guild = message.guild

        # hit-cache
        hits = await hit_cache.get(user.id) or 0
        hits += 1
        await hit_cache.set(user.id, hits, ttl=3600)

        is_soft = hits <= 2 and not force_harsh

        punishment = (
            "Наказание не применяется, за исключением удаления сообщения"
            if is_soft else
            "Тебе выдан мут на 1 час"
        )

        # LOG EMBED
        log_desc = (
            f"{'Удалено сообщение от' if is_soft else 'Участнику выдан мут'} "
            f"{user.mention} (`@{user}`)\n"
            f"Причина: {reason_text}\n\n"
            f"{extra_info}"
        )

        log_embed = discord.Embed(
            title=reason_title,
            description=log_desc,
            color=0xff0000
        )
        log_embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        log_embed.set_footer(text=f"ID: {user.id}")
        log_embed.set_thumbnail(url=user.display_avatar.url)
        log_embed.add_field(
            name="Канал:",
            value=f"{message.channel.mention} (`#{message.channel.name}`)",
            inline=False
        )

        await self.safe_send_to_log(embed=log_embed)

        # MENTION EMBED
        mention_desc = (
            f"Причина срабатывания: {reason_text}\n"
            f"{punishment}\n\n"
            f"{extra_info}\n"
            f"-# Дополнительную информацию можно посмотреть в канале автомодерации"
        )

        mention_embed = discord.Embed(
            title=reason_title,
            description=mention_desc,
            color=0xff0000
        )
        mention_embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        mention_embed.set_thumbnail(url=user.display_avatar.url)
        mention_embed.set_footer(
            text="Если ты считаешь, что это ошибка, проигнорируй это сообщение" if is_soft
                else "Если ты считаешь, что это ошибка, обратись к модераторам"
        )

        await self.safe_send_to_channel(
            message.channel,
            content=user.mention,
            embed=mention_embed
        )

        await self.safe_delete(message)

        # выдаёт мут
        if not is_soft and timeout_reason:
            await self.safe_timeout(user, timedelta(hours=1), timeout_reason)
            await hit_cache.delete(user.id)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # базовые проверки
        if message.author == self.bot.user:
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.guild.id != config.GUILD_ID:
            return
        
        # расстановка приоритетов
        priority: int = 2

        if message.channel.permissions_for(message.author).manage_messages:
            priority = 0
        elif message.channel.id in config.ADS_CHANNELS_IDS:
            priority = 0
        else:
            now = datetime.now(timezone.utc)
            if message.author.joined_at and (now - message.author.joined_at) > timedelta(weeks=2):
                priority = 1

        # модерация активности

        if message.activity is not None:

            # условия срабатывания
            if priority > 1:

                activity_info = (
                    f"Тип: {message.activity.get('type')}\n"
                    f"Party ID: {message.activity.get('party_id')}\n"
                )

                await self.handle_violation(
                    message,
                    reason_title="Реклама через активность",
                    reason_text="реклама через Discord Activity",
                    extra_info=f"Информация об активности:\n```\n{activity_info}```",
                    timeout_reason="Реклама через активность"
                )

                return
                
        
        # модерация сообщений
        if message.content:
                
                # защита от засирания чата 
                if priority > 0:
                
                    if await is_spam_block(message.content):

                        await self.handle_violation(
                            message,
                            reason_title="Спам / засорение чата",
                            reason_text="засорение чата (пустые строки / мусор / код-блоки)",
                            timeout_reason="Спам / засорение чата"
                        )

                        return
                
                # детект рекламы
                if priority > 1:

                    matched = await detect_links(message.content)

                    if matched:

                        # первые 300 символов сообщения
                        preview = message.content[:300].replace("`", "'")

                        extra = (
                            f"Совпадение:\n```\n{matched}\n```\n"
                            f"Первые 300 символов:\n```\n{preview}\n```"
                        )

                        await self.handle_violation(
                            message,
                            reason_title="Реклама в сообщении",
                            reason_text="реклама в тексте сообщения",
                            extra_info=extra,
                            timeout_reason="Реклама в сообщении"
                        )

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

                    extra = (
                        f"Совпадение:\n```\n{matched}\n```\n"
                        f"Информация о файле:\n```\n{file_info}```\n"
                        f"Первые 300 символов:\n```\n{preview}\n```"
                    )

                    await self.handle_violation(
                        message,
                        reason_title="Реклама внутри файла",
                        reason_text="реклама в прикреплённом файле",
                        extra_info=extra,
                        timeout_reason="Реклама в файле",
                        force_harsh=True
                    )

                    return
                
    async def safe_ban(self, guild: discord.Guild, member: discord.abc.Snowflake, reason: str = None, delete_message_seconds: int = 0):
        try:
            await guild.ban(member, reason=reason, delete_message_seconds=delete_message_seconds)
        except Exception:
            pass
                
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        if guild.id != config.GUILD_ID:
            return

        if channel.id not in config.PROTECTED_CHANNELS_IDS:
            return

        # Ищем кто удалил канал
        await asyncio.sleep(1)

        who_deleted: typing.List[typing.Union[discord.User, discord.Member]] = []

        try:
            async for entry in guild.audit_logs(limit=15, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    if entry.user.id != self.bot.user.id:
                        who_deleted.append(entry.user)
                    break
        except:
            pass

        # Если удалил бот -> ищем кто добавил бота (в течение 3 дней)
        resolved: typing.List[typing.Union[discord.User, discord.Member]] = []

        for user in who_deleted:
            resolved.append(user)
            if user.bot:
                try:
                    async for entry in guild.audit_logs(
                        limit=10,
                        action=discord.AuditLogAction.bot_add,
                        after=datetime.now(timezone.utc) - timedelta(days=3)
                    ):
                        if entry.target.id == user.id:
                            resolved.append(entry.user)
                            break
                except:
                    pass

        # Никого не нашли -> подозрение на краш
        if not resolved:
            embed = discord.Embed(
                title="Удаление защищённого канала",
                description=(
                    f"Защищённый канал `#{channel.name}` ({channel.id}) был удалён, но не удалось определить, кем именно\n"
                    f"Возможная причина: попытка краша сервера"
                ),
                color=0xFF0000
            )
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
            embed.set_footer(text="Удаливший не найден")
            embed.add_field(name="Канал:", value=f"`#{channel.name}` (`{channel.id}`)")

            return await self.safe_send_to_log(embed=embed)

        # Находим всех + баним каждого
        embeds = []

        for i, user in enumerate(resolved, 1):
            reason = f"Удаление защищённого канала #{channel.name} ({channel.id})"

            embed = discord.Embed(
                title="Удаление защищённого канала",
                description=(
                    f"{user.mention} (`@{user}`) был забанен.\n"
                    f"Причина: удаление защищённого канала `#{channel.name}` (`{channel.id}`)\n"
                    f"Возможная причина: попытка краша сервера"
                ),
                color=0xFF0000,
            )
            embed.set_footer(text=f"ID: {user.id}")
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Канал:", value=f"`#{channel.name}` (`{channel.id}`)")

            if i == 1:
                embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

            embeds.append(embed)

            await self.safe_ban(guild, user, reason=reason)

        await self.safe_send_to_log(embeds=embeds)

async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoModeration(bot))