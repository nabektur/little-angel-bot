import re
import unicodedata
import urllib.parse

from cache     import AsyncTTL
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
    if len(word) < 6:
        return False
    score = fuzz.partial_ratio("discord", word)
    return score >= threshold

def extract_markdown_links(text: str):
    """Извлекает URL из markdown-разметки [текст](url)"""
    return re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', text)

def is_natural_word_context(text: str, match_pos: int, match_len: int) -> bool:
    """
    Проверяет, находится ли совпадение в естественном контексте слова.
    Возвращает True, если это часть обычного предложения.
    """
    # Берем контекст вокруг совпадения
    start = max(0, match_pos - 20)
    end = min(len(text), match_pos + match_len + 20)
    context = text[start:end].lower()
    
    # Признаки естественного текста
    natural_indicators = [
        # Русские слова рядом
        r'[а-яё]{3,}',
        # Знаки препинания
        r'[,;:!?]',
        # Типичные русские предлоги/союзы
        r'\b(и|в|на|с|что|как|это|для|от|по|но|а|или)\b',
    ]
    
    for pattern in natural_indicators:
        if re.search(pattern, context):
            return True
    
    return False

def extract_spaced_patterns(text: str, compact: str):
    """
    Ищет намеренно разнесенные паттерны вида 't . m e' или 'd i s c o r d . g g'
    """
    findings = []
    
    # Паттерны для поиска с учетом пробелов и разделителей
    patterns = [
        # t.me с разделителями
        (r't[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}m[\s\.\-_•]{0,3}e[\s\.\-_•]{0,3}/[\s\.\-_•]{0,3}\w+', "t.me"),
        (r't[\s\.\-_•]{1,3}m[\s\.\-_•]{1,3}e[\s\.\-_•]{0,3}/[\s\.\-_•]{0,3}\w+', "t.me"),
        
        # discord.gg с разделителями
        (r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}o[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}g[\s\.\-_•]{0,3}g', "discord.gg"),
        (r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}g[\s\.\-_•]{0,3}g', "discord.gg"),
        
        # discordapp с разделителями  
        (r'd[\s\.\-_•]{0,2}i[\s\.\-_•]{0,2}s[\s\.\-_•]{0,2}c[\s\.\-_•]{0,2}o[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}d[\s\.\-_•]{0,2}a[\s\.\-_•]{0,2}p[\s\.\-_•]{0,2}p', "discordapp.com"),
        
        # telegram с разделителями
        (r't[\s\.\-_•]{0,2}e[\s\.\-_•]{0,2}l[\s\.\-_•]{0,2}e[\s\.\-_•]{0,2}g[\s\.\-_•]{0,2}r[\s\.\-_•]{0,2}a[\s\.\-_•]{0,2}m[\s\.\-_•]{0,3}\.[\s\.\-_•]{0,3}(me|org)', "telegram"),
    ]
    
    text_lower = text.lower()
    
    for pattern, label in patterns:
        matches = re.finditer(pattern, text_lower)
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
    dom1 = re.findall(r"([a-zA-Z0-9]+)\.([a-zA-Z]{2,6})\b", text_no_spaces)
    for a, b in dom1:
        candidates.append(a + "." + b)

    # Склеенные домены - более осторожный подход
    dom2 = re.findall(r"([a-zA-Z0-9]{6,})(gg|com|app)\b", text_no_spaces)
    for a, b in dom2:
        candidates.append(a + b)

    return candidates

@AsyncTTL(time_to_live=600, maxsize=20000)
async def detect_links(raw_text: str):
    """
    Детектит подозрительные ссылки в тексте
    Возвращает описание найденной ссылки или None
    """
    
    # Пропускаем очень короткие сообщения без явных признаков
    if len(raw_text) < 8:
        return None
    
    # Нормализуем текст
    compact = await normalize_and_compact(raw_text)
    
    # Сначала проверяем разнесенные паттерны (они приоритетнее)
    spaced_findings = extract_spaced_patterns(raw_text, compact)
    if spaced_findings:
        label, matched = spaced_findings[0]
        return f"{label} (замаскированная ссылка: {matched})"
    
    # Шаг 1: Извлекаем ссылки из markdown
    markdown_links = extract_markdown_links(raw_text)
    all_urls_to_check = [raw_text]
    
    for link_text, url in markdown_links:
        all_urls_to_check.append(url)
        all_urls_to_check.append(link_text)
    
    # Шаг 2: Проверяем каждый фрагмент
    for text_fragment in all_urls_to_check:
        result = await _check_single_fragment(text_fragment, raw_text, compact)
        if result:
            return result
    
    return None


async def _check_single_fragment(text_fragment: str, original_text: str, compact: str):
    """Проверяет один фрагмент текста на наличие ссылок"""
    
    # Если compact не передан, вычисляем
    if not compact:
        compact = await normalize_and_compact(text_fragment)

    if "tme" in compact and ("t.me" in text_fragment.lower()):
        return "t.me"
    
    text_lower = text_fragment.replace(" ", "").lower()
    
    # Пропускаем слишком короткие фрагменты
    if len(compact) < 5:
        return None
    
    # --- Discord ---
    # Явные домены
    if "discordgg" in compact:
        # Проверяем, что это не часть обычного русского текста
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
        elif "invite" in compact:
            return "discordapp.com"
    
    # --- Telegram ---
    if "telegramme" in compact or "telegramorg" in compact:
        return "telegram.me" if "telegramme" in compact else "telegram.org"
    
    # t.me - проверяем с учетом контекста
    if "tme" in compact:
        # Ищем позицию в оригинальном тексте
        tme_patterns = [r't\.me/', r't\s*\.\s*me/', r'tme/']
        for pattern in tme_patterns:
            if re.search(pattern, text_lower):
                # Проверяем контекст
                match = re.search(pattern, text_lower)
                if match and not is_natural_word_context(text_fragment, match.start(), len(match.group())):
                    return "t.me"
    
    # --- Доменные структуры ---
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
            
            # Проверяем контекст
            match_pos = text_fragment.lower().find(left)
            if match_pos != -1:
                if is_natural_word_context(text_fragment, match_pos, len(left)):
                    continue
            
            return f"Похоже на ссылку приглашения в Discord сервер ({cand})"
    
    return None