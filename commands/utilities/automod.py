import io
import typing
import discord
import asyncio

from rapidfuzz import fuzz
from datetime import timedelta, datetime, timezone
from discord.ext import commands

from cache import AsyncLRU
from classes.bot import LittleAngelBot
from modules.configuration import config

import re
import unicodedata
from rapidfuzz import fuzz

def remove_diacritics(s: str):
    return ''.join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def collapse_fancy_letters(s: str):
    out = []
    for char in s:
        try:
            name = unicodedata.name(char)
            if "LETTER" in name:
                # выцепляем последнюю латинскую букву из имени
                # например "MATHEMATICAL BOLD SMALL G" -> "G"
                letter = name.split("LETTER")[-1].strip().split()[-1]
                out.append(letter.lower())
            else:
                out.append(char)
        except ValueError:
            out.append(char)
    return "".join(out)

# Гомоглифы (кириллица, греческие, математика)
HOMOGLYPHS = {
    # кириллица -> латиница
    "а": "a", "А": "A",
    "е": "e", "Е": "E",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "с": "c", "С": "C",
    "х": "x", "Х": "X",
    "у": "y", "У": "Y",
    "к": "k", "К": "K",
    "м": "m", "М": "M",
    "т": "t", "Т": "T",
    "в": "b", "В": "B",
    "й": "i", "Й": "I",
    "ё": "e", "Ё": "E",

    # греческие
    "α": "a", "β": "b", "γ": "y", "δ": "d",
    "ε": "e", "ζ": "z", "η": "h", "ι": "i",
    "κ": "k", "λ": "l", "μ": "m", "ν": "n",
    "ο": "o", "π": "p", "ρ": "p", "σ": "s",
    "τ": "t", "υ": "y", "φ": "f", "χ": "x",
    "ω": "w",

    # похожие знаки
    "○": "o", "●": "o", "•": "o", "∅": "o",
    "｜": "l", "∣": "l",
    "∕": "/",
}
HOMO_MAP = str.maketrans(HOMOGLYPHS)

# leetspeak
LEET_MAP = str.maketrans({
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "b",
    "7": "t",
    "8": "b",
})

# zero-width символы
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF]")

# все не буквенно-цифровые -> пробел
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

INTERFERENCE_RE = re.compile(r"[\u2500-\u257F\u2580-\u259F\u25A0-\u25FF\u2600-\u27BF]+")

# маппинг конкретных emoji-символов
EMOJI_ASCII_MAP = {
    "🅰️": "a", "🅱️": "b", "🅾️": "o", "🅿️": "p",
    "Ⓜ️": "m", "ℹ️": "i", "❌": "x", "⭕": "o",
}


# regional indicator символы 🇦–🇿 (U+1F1E6–U+1F1FF)
REGIONAL_INDICATOR_MAP = {
    chr(code): chr(ord('a') + code - 0x1F1E6)
    for code in range(0x1F1E6, 0x1F1FF + 1)
}

def normalize_unicode_letter(ch: str) -> str:
    decomposed = unicodedata.normalize("NFKD", ch)
    # оставляет только ascii-букву
    if decomposed and 'a' <= decomposed[0].lower() <= 'z':
        return decomposed[0].lower()
    return ch

def replace_emoji_letters(text: str):
    result = []

    for ch in text:

        # точечный маппинг (🅰️ → a)
        if ch in EMOJI_ASCII_MAP:
            result.append(EMOJI_ASCII_MAP[ch])
            continue

        # региональные флаги (🇦 → a)
        if ch in REGIONAL_INDICATOR_MAP:
            result.append(REGIONAL_INDICATOR_MAP[ch])
            continue

        # математические/фуллвид/курсивные символы (𝘢 → a, Ａ → a)
        norm = normalize_unicode_letter(ch)
        if norm != ch:
            result.append(norm)
            continue

        # обычный символ
        result.append(ch)

    return "".join(result)

@AsyncLRU(maxsize=5000)
async def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = ZERO_WIDTH_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)

    # удаляет диакритику (кружки, точки, черточки, комбинируемые символы)
    text = remove_diacritics(text)

    # fancy unicode -> ascii (𝓭 -> d)
    text = collapse_fancy_letters(text)

    # гомоглифы
    text = text.translate(HOMO_MAP)

    # leet
    text = text.translate(LEET_MAP)

    # заменяет emoji-символы на ascii
    text = replace_emoji_letters(text)

    # удаляет emoji-квадраты и декоративные символы
    text = INTERFERENCE_RE.sub(" ", text)

    # приводит к нижнему регистру
    text = text.lower()

    # заменяет всё не алфавитно-цифровое на пробел
    text = NON_ALNUM_RE.sub(" ", text)

    # склеивает d i s c o r d g g → discordgg
    text = re.sub(r"(?<=\b[a-z]) (?=[a-z]\b)", "", text)

    # убирает множественные пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# паттерны ссылок
links_patterns = [
    "discord.gg",
    "discord.com/invite",
    "discordapp.com/invite",
    "t.me/joinchat",
    "t.me",
]


async def find_spam_matches(text: str, patterns=None):
    if not text:
        return False

    norm = await normalize_text(text)
    no_spaces = norm.replace(" ", "")

    if patterns is None:
        patterns = links_patterns

    # Прямое вхождение (с пробелами и без)
    for candidate in (norm, no_spaces):
        for p in patterns:
            if p in candidate:
                return p

    # Нечёткое совпадение по словам
    words = norm.split()[:4000]

    for w in words:
        for p in patterns:
            if fuzz.ratio(w, p) > 80:
                return w

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


        # модерация активности

        if message.activity is not None:

            # если участник зашёл меньше 2 недель назад -> удаляет и логирует
            if message.author.joined_at:
                if (datetime.now(timezone.utc) - message.author.joined_at) < timedelta(weeks=2):

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
        if message.content:

                matched = await find_spam_matches(message.content)

                if matched:

                    # первые 300 символов сообщения
                    preview = message.content[:300].replace("`", "'")

                    log_embed = discord.Embed(
                        title="Реклама в сообщении",
                        description=(
                            f"Удалено сообщение от участника {message.author.mention} (`@{message.author}`)\n"
                            f"Причина: подозрение на рекламу в сообщении\n\n"
                            f"Совпадение:\n```\n{matched}\n```\n"
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
                            f"Совпадение, на которое отреагировал бот:\n```\n{matched}\n```\n\n"
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

        if message.attachments:

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

                matched = await find_spam_matches(content)

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
                            f"Участнику {message.author.mention} (`@{message.author}`) был выдан мут на 1 час.\n"
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
                    log_embed.add_field(name="Канал:", value=message.channel.mention, inline=False)

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