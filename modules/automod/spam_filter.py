import re

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\uFEFF\u2060]")
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