import re

from collections import Counter
from cache       import AsyncTTL

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2060]")
EMPTY_SPAM_LINE_RE = re.compile(r"^[\s\`\u200B-\u200F\uFEFF]{0,}$")

@AsyncTTL(time_to_live=600, maxsize=20000)
async def is_spam_block(message: str) -> bool:
    """
    пустые строки, код-блоки, мусорные символы.
    """

    # --- Символьно-спамовая проверка ---

    # 30 одинаковых подряд (~~~~~~ итд)
    if re.search(r"(.)\1{30,}", message):
        return True

    # Один символ занимает > 65% сообщения

    if len(message) > 50:  # смысл есть только для длинных сообщений
        freq = Counter(message)
        dominant = max(freq.values()) if freq else 0
        if dominant / len(message) >= 0.65:
            return True

        # Один символ встречается очень много раз (>200)
        if any(cnt >= 200 for cnt in freq.values()):
            return True

    # Кавычки
    tick_count = message.count("`")
    if tick_count >= 120 or re.search(r"`{25,}", message):
        return True

    lines = message.split("\n")
    if len(lines) >= 40:
        empty_like = sum(1 for l in lines if EMPTY_SPAM_LINE_RE.match(l))
        if empty_like / len(lines) >= 0.7:
            return True

    # Проверка код-блока
    if message.count("```") >= 2:
        parts = message.split("```")
        for i in range(1, len(parts), 2):
            code = parts[i].strip()
            if len(code) < 8:
                continue
            if len(code) > 1500 or code.count("\n") > 25:
                return True

    if len(message) > 3000:
        compact = re.sub(r"[a-zA-Z0-9а-яА-ЯёЁ]+", "", message)
        if len(compact) / len(message) >= 0.7:
            return True

    if re.search(r"(.)\1{40,}", message):
        return True

    inv = re.findall(ZERO_WIDTH_RE, message)
    if len(inv) > 50:
        return True

    return False