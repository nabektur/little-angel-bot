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
            if not "/channels/" in raw_text.replace(" ", "").lower():
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

            if "/channels/" in raw_text.replace(" ", "").lower():
                continue  # это не ссылка-приглашение

            # ловим только ссылки
            return f"Похоже на ссылку приглашения в Discord сервер ({cand})"

    return None