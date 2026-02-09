import re
import logging
import unicodedata
import urllib.parse
import typing

from aiocache import SimpleMemoryCache
import aiohttp
from cache import AsyncTTL
import discord
from rapidfuzz import fuzz

from classes.bot import LittleAngelBot
from modules.extract_message_content import extract_message_content

VARIATION_SELECTOR_RE = re.compile(r"[\uFE0F]")
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2060]")
MARKDOWN_LINKS_RE = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')

# Паттерны для поиска с учетом пробелов и разделителей
SPACED_LINK_PATTERNS = [
    # t.me с разделителями
    (re.compile(r't[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}m[\s\.\-_•]{0,3}e[\s\.\-_•]{0,3}/[\s\.\-_•]{0,3}\w+'), "t.me"),
    (re.compile(r't[\s\.\-_•]{1,3}m[\s\.\-_•]{1,3}e[\s\.\-_•]{0,3}/[\s\.\-_•]{0,3}\w+'), "t.me"),
    
    # discord.gg с разделителями
    (re.compile(r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}o[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}g[\s\.\-_•]{0,3}g'), "discord.gg"),
    (re.compile(r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}g[\s\.\-_•]{0,3}g'), "discord.gg"),
    
    # discordapp с разделителями  
    (re.compile(r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}o[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,2}a[\s\.\-_•]{0,2}p[\s\.\-_•]{0,2}p'), "discordapp.com"),
    
    # telegram с разделителями
    (re.compile(r't[\s\.\-_•]{0,2}e[\s\.\-_•]{0,2}l[\s\.\-_•]{0,2}e[\s\.\-_•]{0,2}g[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}a[\s\.\-_•]{0,2}m[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}(me|org)'), "telegram"),
]

COLLAPSE_RE = re.compile(r"\s+")
COMPACT_RE = re.compile(r"[^a-z0-9]")

# Признаки естественного текста
NATURAL_INDICATORS_PATTERNS = (
    # Русские слова рядом
    re.compile(r'[а-яё]{3,}'),
    # Знаки препинания
    re.compile(r'[,;:!?]'),
    # Типичные русские предлоги/союзы
    re.compile(r'\b(и|в|на|с|что|как|это|для|от|по|но|а|или)\b')
)

DOMAINS_WITH_DOT_RE = re.compile(r"([a-zA-Z0-9]+)\.([a-zA-Z]{2,6})\b")
GLUED_DOMAINS_RE = re.compile(r"([a-zA-Z0-9]{6,})(gg|com|app)\b")

EXPLICIT_URL_PATTERNS = [
    (re.compile(r'https?://discord\.gg/\w+', re.IGNORECASE), 'discord.gg (явная ссылка)'),
    (re.compile(r'https?://discord\.com/invite/\w+', re.IGNORECASE), 'discord.com/invite (явная ссылка)'),
    (re.compile(r'https?://discordapp\.com/invite/\w+', re.IGNORECASE), 'discordapp.com/invite (явная ссылка)'),
    (re.compile(r'https?://t\.me/\w+', re.IGNORECASE), 't.me (явная ссылка)'),
]

TME_SPECIAL_PATTERNS = (
    re.compile(r't\.me/'),
    re.compile(r't\s*\.\s*me/'),
    re.compile(r'tme/'),
)

FUZZY_INVITE_RE = re.compile(r'invit|nvite|vite')
DISCORDGG_RE = re.compile(r'discordgg')

# Паттерны для детекции Discord invite в URL
DISCORD_INVITE_PATTERNS = [
    re.compile(r"discord\.com/invite/", re.IGNORECASE),
    re.compile(r"discord\.gg/", re.IGNORECASE),
    re.compile(r"discordapp\.com/invite/", re.IGNORECASE),
]

# Паттерн для извлечения всех URL из текста
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)

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

# Кириллица -> латиница (расширенная версия)
HOMOGLYPHS = {
    "а": "a", "А": "a",
    "е": "e", "Е": "e", "ё": "e", "Ё": "e",
    "о": "o", "О": "o",
    "р": "p", "Р": "p",
    "с": "c", "С": "c",
    "х": "x", "Х": "x",
    "у": "y", "У": "y",
    "к": "k", "К": "k",
    "м": "m", "М": "m",
    "т": "t", "Т": "t",
    "в": "b", "В": "b",
    "н": "h", "Н": "h",
    "д": "d", "Д": "d",
    "г": "g", "Г": "g",
    "б": "b", "Б": "b",
    "і": "i", "І": "i",
    # Цифры и символы
    "0": "o",
    "1": "l",
    "3": "e",
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
_COMBINED_MAP.update(HOMOGLYPHS)
_COMBINED_MAP.update(FANCY_MAP)

# СТРОГИЙ ПАТТЕРН ИНВАЙТ КОДОВ
STRICT_INVITE_CODE_PATTERN = re.compile(
    r'\b(?=\S*[A-Z])(?=\S*[a-z])[a-zA-Z0-9\-]{5,20}\b'
)

# Паттерн для вырезания URL из текста перед парсингом
URL_PATTERN_FOR_EXTRACTING_WORDS = re.compile(
    r'https?://[^\s\.,;!?\(\)\[\]\{\}<>«»"\']*'
    r'|[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
)

DATE_RE = re.compile(r'^\d{2,4}-\d{2}')
DISCORD_EMOJI_PATTERN = re.compile(r'<a?:[^:>]+:\d{17,20}>|:[^:\s]+:')

INVITE_CODE_CACHE = SimpleMemoryCache()
INVITE_CODE_CACHE_TTL = 1200

WHITELISTED_WORDS = ("spotify",)

def should_skip_potential_code(code: str) -> bool:
    """Фильтрует явно невалидные коды"""
    
    # В инвайт-коде ВСЕГДА есть латинские буквы
    if not any(c.isalpha() and c.isascii() for c in code):
        return True

    # Паттерны дат (2024-01, 2024-12-31)
    if DATE_RE.match(code):
        return True
    
    if any(w in code.lower() for w in WHITELISTED_WORDS):
        return True
    
    return False

async def check_potential_invite_code(bot: LittleAngelBot, code: str) -> dict:
    """
    Проверяет код через Discord API с кэшированием
    
    Args:
        bot: Экземпляр discord.Bot для API запросов
        code: Потенциальный инвайт-код
    
    Returns:
        dict: {'is_invite': bool, 'guild_id': int|None, 'guild_name': str|None, 'from_cache': bool}
    """
    
    # Ключ для кэша (lowercase для избежания дубликатов)
    cache_key = f"invite_code:{code.lower()}"
    
    # Проверяем кэш
    cached = await INVITE_CODE_CACHE.get(cache_key)
    if cached is not None:
        logging.debug(f"Инвайт-код {code} найден в кэше: {cached}")
        return {
            'is_invite': cached['is_valid'],
            'guild_id': cached.get('guild_id'),
            'guild_name': cached.get('guild_name'),
            'member_count': cached.get('member_count'),
            'from_cache': True
        }
    
    # Проверяем через Discord API
    try:
        invite = await bot.fetch_invite(code, with_counts=True)
        
        guild_id = invite.guild.id if invite.guild else None
        guild_name = invite.guild.name if invite.guild else None
        member_count = getattr(invite, 'approximate_member_count', None)
        
        # Кэшируем результат (валидный инвайт)
        result = {
            'is_valid': True,
            'guild_id': guild_id,
            'guild_name': guild_name,
            'member_count': member_count
        }
        await INVITE_CODE_CACHE.set(cache_key, result, ttl=INVITE_CODE_CACHE_TTL)
        
        return {
            'is_invite': True,
            'guild_id': guild_id,
            'guild_name': guild_name,
            'member_count': member_count,
            'from_cache': False
        }
        
    except discord.NotFound:
        # Невалидный инвайт - кэшируем как невалидный
        result = {
            'is_valid': False,
            'guild_id': None,
            'guild_name': None
        }
        await INVITE_CODE_CACHE.set(cache_key, result, ttl=INVITE_CODE_CACHE_TTL)
        
        logging.debug(f"Инвайт-код {code} проверен через API: невалидный (404)")
        
        return {
            'is_invite': False,
            'guild_id': None,
            'guild_name': None,
            'from_cache': False
        }
        
    except discord.HTTPException as e:
        # Ошибка API - НЕ кэшируем (может быть временная проблема)
        logging.warning(f"Ошибка API при проверке кода {code}: {e}")
        
        return {
            'is_invite': False,
            'guild_id': None,
            'guild_name': None,
            'from_cache': False,
            'error': str(e)
        }
    
    except Exception as e:
        # Неожиданная ошибка
        logging.error(f"Неожиданная ошибка при проверке кода {code}: {e}")
        
        return {
            'is_invite': False,
            'guild_id': None,
            'guild_name': None,
            'from_cache': False,
            'error': str(e)
        }

async def extract_potential_invite_codes(bot: LittleAngelBot, message: discord.Message) -> list:
    """
    Извлекает потенциальные Discord invite коды из текста
    ОПТИМИЗИРОВАННАЯ ВЕРСИЯ - regex делает всю работу
    """
    
    text = await extract_message_content(bot, message)

    clean_text = DISCORD_EMOJI_PATTERN.sub(' ', text)
    
    # Убираем URL из текста, чтобы не ловить части ссылок
    clean_text = URL_PATTERN_FOR_EXTRACTING_WORDS.sub(' ', clean_text)
    
    # Извлекаем все совпадения с паттерном
    matches = STRICT_INVITE_CODE_PATTERN.findall(clean_text)
    
    # Минимальная фильтрация (только критичные случаи)
    filtered_codes = [code for code in matches if not should_skip_potential_code(code)]
    
    # Убираем дубликаты (case-insensitive)
    seen = set()
    unique_codes = []
    for code in filtered_codes:
        code_lower = code.lower()
        if code_lower not in seen:
            seen.add(code_lower)
            unique_codes.append(code)
    
    # Ограничиваем количество для проверки (не более 5)
    return unique_codes[:5]

async def check_message_for_invite_codes(bot: LittleAngelBot, message: discord.Message, current_guild_id: int) -> dict:
    """
    Проверяет сообщение на наличие валидных Discord invite кодов
    ЭТА ФУНКЦИЯ ДОЛЖНА ВЫЗЫВАТЬСЯ ТОЛЬКО ДЛЯ НОВЫХ УЧАСТНИКОВ!
    
    Args:
        bot: Экземпляр discord.Bot для API запросов
        message: Экземпляр discord.Message для проверки
        current_guild_id: ID текущего сервера (чтобы не банить за свои инвайты)
    
    Returns:
        dict: {
            'found_invite': bool,
            'invite_code': str|None,
            'guild_id': int|None,
            'guild_name': str|None,
            'from_cache': bool
        }
    """
    
    # Извлекаем потенциальные коды
    potential_codes = extract_potential_invite_codes(bot, message)
    
    if not potential_codes:
        return {'found_invite': False}
    
    logging.debug(f"Найдено {len(potential_codes)} потенциальных кодов для проверки: {potential_codes}")
    
    # Проверяем каждый код через API
    for code in potential_codes:
        result = await check_potential_invite_code(bot, code)
        
        if result['is_invite']:
            # Проверяем, не инвайт ли это на текущий сервер
            if result['guild_id'] == current_guild_id:
                logging.debug(f"Код {code} ведёт на свой сервер, пропускаем")
                continue
            
            # Найден валидный инвайт на другой сервер!
            return {
                'found_invite': True,
                'invite_code': code,
                'guild_id': result['guild_id'],
                'guild_name': result['guild_name'],
                'from_cache': result.get('from_cache', False),
                'member_count': result.get('member_count')
            }
    
    return {'found_invite': False}

def is_discord_invite_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой-приглашением Discord"""
    for pattern in DISCORD_INVITE_PATTERNS:
        if pattern.search(url):
            return True
    return False

@AsyncTTL(time_to_live=300, maxsize=1000)
async def check_url_redirect(url: str, max_redirects: int = 5) -> str:
    """
    Проверяет финальный URL после всех редиректов
    Кэширует результат на 5 минут
    """
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                allow_redirects=True,
                max_redirects=max_redirects,
                headers={'User-Agent': 'Mozilla/5.0'}
            ) as response:
                return str(response.url)
    except Exception as e:
        logging.debug(f"Error checking redirect for {url}: {e}")
        # В случае ошибки возвращаем исходный URL
        return url


def extract_urls_from_text(text: str) -> list:
    """Извлекает все HTTP/HTTPS URL из текста"""
    urls = URL_PATTERN.findall(text)
    return urls


async def check_urls_for_discord_invites(text: str) -> str:
    """
    Проверяет URL в тексте на редиректы к Discord invite
    Возвращает описание найденной ссылки или None
    """
    urls = extract_urls_from_text(text)
    
    if not urls:
        return None
    
    # Сначала проверяем прямые Discord invite ссылки
    for url in urls:
        if is_discord_invite_url(url):
            return "discord.gg/invite (прямая ссылка через URL)"
    
    # Ограничиваем количество проверок (чтобы не перегружать)
    suspicious_urls = urls[:3]
    
    for url in suspicious_urls:
        try:
            # Добавляем схему, если отсутствует
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            final_url = await check_url_redirect(url)
            
            if is_discord_invite_url(final_url):
                return f"discord.gg/invite (через переходник {url})"
        except Exception as e:
            logging.debug(f"Error checking URL {url}: {e}")
            continue
    
    return None

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
        for token in nm:
            if len(token) == 1 and 'A' <= token <= 'Z':
                return token.lower()

    return " "

async def normalize_and_compact(raw_text: str) -> str:

    text = unicodedata.normalize("NFKC", raw_text)

    out = []
    for ch in text:
        out.append(await _char_to_ascii(ch))

    collapsed = "".join(out)
    collapsed = COLLAPSE_RE.sub(" ", collapsed).strip()
    compact = COMPACT_RE.sub("", collapsed.lower())
    return compact

async def looks_like_discord(word: str, threshold=85):
    """Повышен порог с 70 до 85 для уменьшения ложных срабатываний"""
    if len(word) < 6:
        return False
    score = fuzz.partial_ratio("discord", word)
    return score >= threshold

def extract_markdown_links(text: str):
    """Извлекает URL из markdown-разметки [текст](url)"""
    return re.findall(MARKDOWN_LINKS_RE, text)

def is_natural_word_context(text: str, match_pos: int, match_len: int) -> bool:
    """
    Проверяет, находится ли совпадение в естественном контексте слова.
    Возвращает True, если это часть обычного предложения.
    """
    # Берем контекст вокруг совпадения
    start = max(0, match_pos - 20)
    end = min(len(text), match_pos + match_len + 20)
    context = text[start:end].lower()
    
    for pattern in NATURAL_INDICATORS_PATTERNS:
        if pattern.search(context):
            return True
    
    return False

def extract_spaced_patterns(text: str, compact: str):
    """
    Ищет намеренно разнесенные паттерны вида 't . m e' или 'd i s c o r d . g g'
    """
    findings = []
    
    text_lower = text.lower()
    
    for pattern, label in SPACED_LINK_PATTERNS:
        matches = pattern.finditer(text_lower)
        for match in matches:
            # Проверяем контекст
            if not is_natural_word_context(text, match.start(), len(match.group())):
                findings.append((label, match.group()))
    
    return findings

def extract_possible_domains(text: str):
    """Извлекает возможные домены из текста"""
    text_no_spaces = text.replace(" ", "")
    candidates = []

    # Стандартные домены с точкой
    dom1 = DOMAINS_WITH_DOT_RE.findall(text_no_spaces)
    for a, b in dom1:
        candidates.append(a + "." + b)

    # Склеенные домены - более осторожный подход
    dom2 = GLUED_DOMAINS_RE.findall(text_no_spaces)
    for a, b in dom2:
        candidates.append(a + b)

    return candidates


@AsyncTTL(time_to_live=600, maxsize=20000)
async def detect_links(bot: LittleAngelBot, message: typing.Union[discord.Message, str]):
    """
    Детектит подозрительные ссылки в тексте
    Возвращает описание найденной ссылки или None
    """

    if isinstance(message, discord.Message):
        raw_text = await extract_message_content(bot, message)
    else:
        raw_text = message

    # Проверка URL-переходников на Discord invite
    redirect_result = await check_urls_for_discord_invites(raw_text)
    if redirect_result:
        return redirect_result
    
    # Многократное декодирование URL
    decoded_text = raw_text
    for _ in range(5):
        try:
            new_decoded = urllib.parse.unquote(decoded_text)
            if new_decoded == decoded_text:
                break
            decoded_text = new_decoded
        except Exception:
            break
    
    # Нормализуем декодированный текст
    compact = await normalize_and_compact(decoded_text)
    
    # Проверка 1: Явные паттерны на декодированном тексте
    for pattern, label in EXPLICIT_URL_PATTERNS:
        if pattern.search(decoded_text):
            return label
    
    # Проверка 2: Усиленные паттерны на компактном варианте
    # Используем fuzzy matching для "invite" (минимум 4 из 6 букв подряд)
    if "discord" in compact:
        # Ищем "invit", "nvite", "invite" и т.д.
        if FUZZY_INVITE_RE.search(compact):
            return "discord.com/invite (замаскированная через encoding)"
    
    if DISCORDGG_RE.search(compact):
        return "discord.gg (замаскированная)"
    
    if "discordapp" in compact and FUZZY_INVITE_RE.search(compact):
        return "discordapp.com/invite (замаскированная через encoding)"
    
    if TME_SPECIAL_PATTERNS[2].search(compact):
        return "t.me (замаскированная)"
    
    # Пропускаем очень короткие сообщения
    if len(raw_text) < 8:
        return None
    
    # Проверяем разнесенные паттерны
    spaced_findings = extract_spaced_patterns(decoded_text, compact)
    if spaced_findings:
        label, matched = spaced_findings[0]
        return f"{label} (замаскированная ссылка: {matched})"
    
    # Извлекаем ссылки из markdown
    markdown_links = extract_markdown_links(decoded_text)
    all_urls_to_check = [decoded_text]
    
    for link_text, url in markdown_links:
        all_urls_to_check.append(url)
        all_urls_to_check.append(link_text)
    
    # Проверяем каждый фрагмент
    for text_fragment in all_urls_to_check:
        result = await _check_single_fragment(text_fragment, decoded_text, compact)
        if result:
            return result
    
    return None


async def _check_single_fragment(text_fragment: str, original_text: str, compact: str):
    """Проверяет один фрагмент текста на наличие ссылок"""
    
    # Если compact не передан, вычисляем
    if not compact:
        compact = await normalize_and_compact(text_fragment)

    if "tme" in compact and ("t.me" in text_fragment.lower() or "tme/" in text_fragment.lower()):
        return "t.me"
    
    text_lower = text_fragment.replace(" ", "").lower()
    
    # Пропускаем слишком короткие фрагменты
    if len(compact) < 5:
        return None
    
    # --- Discord ---
    # Проверяем наличие discord + частичное совпадение с invite
    if "discord" in compact:
        # Ищем частичные совпадения с "invite" (минимум 4 буквы подряд)
        invite_parts = ['invit', 'nvite', 'vite']
        if any(part in compact for part in invite_parts):
            match_pos = text_fragment.lower().find("discord")
            if match_pos != -1:
                if is_natural_word_context(text_fragment, match_pos, 7):
                    return None
            return "discord.com/invite"
        
        # Проверка на discord.gg
        if compact.endswith("gg") or "discordgg" in compact:
            match_pos = text_fragment.lower().find("discord")
            if match_pos != -1:
                if is_natural_word_context(text_fragment, match_pos, 7):
                    return None
            return "discord.gg"
    
    # Явные домены
    if "discordgg" in compact:
        match_pos = text_fragment.lower().find("discord")
        if match_pos != -1:
            if is_natural_word_context(text_fragment, match_pos, 7):
                return None
        return "discord.gg"
    
    if "discordcom" in compact:
        if "/channels/" not in text_lower:
            match_pos = text_fragment.lower().find("discord")
            if match_pos != -1:
                if is_natural_word_context(text_fragment, match_pos, 7):
                    return None
            return "discord.com"
    
    if "discordappcom" in compact:
        if not any(x in original_text for x in ["https://cdn.discordapp.com", "https://media.discordapp.net", "https://images-ext-1.discordapp.net"]):
            return "discordapp.com"
        elif any(part in compact for part in ['invit', 'nvite']):
            return "discordapp.com/invite"
    
    # --- Telegram ---
    if "telegramme" in compact or "telegramorg" in compact:
        return "telegram.me" if "telegramme" in compact else "telegram.org"
    
    # t.me - проверяем с учетом контекста
    if "tme" in compact:
        for pattern in TME_SPECIAL_PATTERNS:
            if pattern.search(text_lower):
                match = pattern.search(text_lower)
                if match and not is_natural_word_context(text_fragment, match.start(), len(match.group())):
                    return "t.me"
    
    # --- Доменные структуры ---
    candidates = extract_possible_domains(compact)
    
    for cand in candidates:
        if len(cand) < 8:
            continue
            
        left = cand.split(".")[0].replace("gg","").replace("com","").replace("app","")
        
        if await looks_like_discord(left):
            if left == "discord":
                continue
            
            if any(x in cand for x in ["imagesext1discordapp", "mediadiscordapp", "cdndiscordapp"]):
                if not any(part in compact for part in ['invit', 'nvite']):
                    continue
            
            if "/channels/" in text_lower:
                continue
            
            match_pos = text_fragment.lower().find(left)
            if match_pos != -1:
                if is_natural_word_context(text_fragment, match_pos, len(left)):
                    continue
            
            return f"Похоже на ссылку приглашения в Discord сервер ({cand})"
    
    return None

async def check_message_for_invite_codes(bot: LittleAngelBot, message: discord.Message, current_guild_id: int) -> dict:
    """
    Проверяет сообщение на наличие валидных Discord invite кодов
    ЭТА ФУНКЦИЯ ДОЛЖНА ВЫЗЫВАТЬСЯ ТОЛЬКО ДЛЯ НОВЫХ УЧАСТНИКОВ!
    """
    
    # Извлекаем потенциальные коды
    potential_codes = await extract_potential_invite_codes(bot, message)
    
    if not potential_codes:
        return {'found_invite': False}
    
    logging.debug(f"Найдено {len(potential_codes)} потенциальных кодов: {potential_codes}")
    
    # Проверяем каждый код через API (с кэшированием)
    for code in potential_codes:
        result = await check_potential_invite_code(bot, code)
        
        if result['is_invite']:
            # Проверяем, не инвайт ли это на текущий сервер
            if result['guild_id'] == current_guild_id:
                logging.debug(f"Код {code} ведёт на свой сервер, пропускаем")
                continue
            
            # Найден валидный инвайт на другой сервер!
            logging.warning(f"Обнаружен инвайт-код: {code} → {result['guild_name']} (кэш: {result['from_cache']})")
            return {
                'found_invite': True,
                'invite_code': code,
                'guild_id': result['guild_id'],
                'guild_name': result['guild_name'],
                'from_cache': result['from_cache'],
                'member_count': result.get('member_count')
            }
    
    return {'found_invite': False}