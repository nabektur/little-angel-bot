import re
import unicodedata
import urllib.parse

from cache     import AsyncLRU
from rapidfuzz import fuzz

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

async def looks_like_discord(word: str, threshold=85):
    """Повышен порог с 70 до 85 для уменьшения ложных срабатываний"""
    if len(word) < 6:  # Увеличен минимум с 5 до 6
        return False
    score = fuzz.partial_ratio("discord", word)
    return score >= threshold

def extract_markdown_links(text: str):
    """Извлекает URL из markdown-разметки [текст](url)"""
    return re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', text)

def has_url_markers(text: str) -> bool:
    """Проверяет наличие явных маркеров URL (http, //, точка с доменом)"""
    text_lower = text.lower()
    
    # Явные протоколы
    if "http://" in text_lower or "https://" in text_lower:
        return True
    
    # Двойной слэш без пробелов вокруг
    if re.search(r'\S//\S', text):
        return True
    
    # Домен с точкой и известным TLD
    if re.search(r'\w+\.(com|gg|net|org|app|io|me|xyz|ru|lv)\b', text_lower):
        return True
    
    return False

def extract_possible_domains(text: str):
    """Извлекает возможные домены из текста"""
    text_no_spaces = text.replace(" ", "")
    candidates = []

    # Стандартные домены с точкой
    dom1 = re.findall(r"([a-zA-Z0-9]+)\.([a-zA-Z]{2,6})\b", text_no_spaces)
    for a, b in dom1:
        candidates.append(a + "." + b)

    # Склеенные домены (только если есть явные маркеры URL)
    if has_url_markers(text):
        dom2 = re.findall(r"([a-zA-Z0-9]{5,})(gg|com|app|net)", text_no_spaces)
        for a, b in dom2:
            # Проверяем, что это не часть обычного слова
            if len(a) > 10:  # Слишком длинное слово подозрительно
                candidates.append(a + b)

    return candidates

@AsyncLRU(maxsize=5000)
async def detect_links(raw_text: str):
    """
    Детектит подозрительные ссылки в тексте
    Возвращает описание найденной ссылки или None
    """
    
    # Быстрая проверка: если текст короткий и без URL-маркеров, пропускаем
    if len(raw_text) < 10 and not has_url_markers(raw_text):
        return None
    
    # Шаг 1: Извлекаем ссылки из markdown
    markdown_links = extract_markdown_links(raw_text)
    all_urls_to_check = [raw_text]
    
    for link_text, url in markdown_links:
        all_urls_to_check.append(url)
        all_urls_to_check.append(link_text)
    
    # Шаг 2: Проверяем каждый фрагмент
    for text_fragment in all_urls_to_check:
        result = await _check_single_fragment(text_fragment, raw_text)
        if result:
            return result
    
    return None

async def _check_single_fragment(text_fragment: str, original_text: str):
    """Проверяет один фрагмент текста на наличие ссылок"""
    
    # Нормализуем текст
    compact = await normalize_and_compact(text_fragment)
    text_lower = text_fragment.replace(" ", "").lower()
    
    # Пропускаем слишком короткие фрагменты
    if len(compact) < 5:
        return None
    
    # --- Discord ---
    # Явные домены
    if "discordgg" in compact or "discordcom" in compact or "discordappcom" in compact:
        if "discordgg" in compact:
            return "discord.gg"
        if "discordcom" in compact:
            if "/channels/" not in text_lower:
                return "discord.com"
        if "discordappcom" in compact:
            if not any(x in original_text for x in ["https://cdn.discordapp.com", "https://media.discordapp.net", "https://images-ext-1.discordapp.net"]):
                return "discordapp.com"
            elif "invite" in compact:
                return "discordapp.com"
    
    # --- Telegram ---
    # Проверяем только если есть явные признаки ссылки
    if has_url_markers(text_fragment):
        if "telegramme" in compact or "telegramorg" in compact:
            return "telegram.me" if "telegramme" in compact else "telegram.org"
        
        # t.me только если есть слэш или точка рядом
        if re.search(r't\.me/\w+', text_lower) or re.search(r't\.me\s', text_lower):
            return "t.me"
        
        if re.search(r"(telegram\.me|telegram\.org)/", text_lower):
            m = re.search(r"(telegram\.me|telegram\.org)", text_lower)
            return m.group(1)
    
    # --- Доменные структуры ---
    # Проверяем только если есть явные признаки URL
    if not has_url_markers(text_fragment):
        return None
    
    candidates = extract_possible_domains(compact)
    
    for cand in candidates:
        # Пропускаем короткие кандидаты
        if len(cand) < 8:
            continue
            
        left = cand.split(".")[0].replace("gg","").replace("com","").replace("app","")
        
        if await looks_like_discord(left):
            # Исключаем обычное слово "discord"
            if left == "discord":
                continue
            
            # Исключаем CDN
            if any(x in cand for x in ["imagesext1discordapp", "mediadiscordapp", "cdndiscordapp"]):
                if "invite" not in compact:
                    continue
            
            # Исключаем внутренние ссылки
            if "/channels/" in text_lower:
                continue
            
            return f"Похоже на ссылку приглашения в Discord сервер ({cand})"
    
    return None