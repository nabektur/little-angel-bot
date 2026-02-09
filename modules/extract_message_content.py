import logging

from cache import AsyncTTL
import discord
from discord.ext.commands import clean_content

from classes.bot import LittleAngelBot

@AsyncTTL(time_to_live=30)
async def activity_to_dict(activity):
    """Преобразует объект активности в словарь со всеми полями"""
    if isinstance(activity, dict):
        return activity
    
    result = {}
    for attr in dir(activity):
        if not attr.startswith('_') and not callable(getattr(activity, attr, None)):
            try:
                value = getattr(activity, attr)
                if value is not None and not hasattr(value, '__dict__'):
                    result[attr] = value
            except Exception:
                continue
    return result

@AsyncTTL(time_to_live=30)
async def format_dict_fields(data, indent=0):
    lines = []
    prefix = "  " * indent
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(await format_dict_fields(value, indent + 1))
        elif isinstance(value, (list, tuple)):
            if value:
                lines.append(f"{prefix}{key}: {', '.join(str(v) for v in value)}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    
    return '\n'.join(lines)

@AsyncTTL(time_to_live=5)
async def clean_message_text(bot: LittleAngelBot, message: discord.Message):
    cleaner = clean_content(
        fix_channel_mentions=True,
        use_nicknames=True,
        escape_markdown=True
    )

    ctx = await bot.get_context(message)

    cleaned = await cleaner.convert(ctx, message.content)
    return cleaned

@AsyncTTL(time_to_live=5)
async def extract_message_content(bot: LittleAngelBot, message: discord.Message) -> str:

    message_content = ""

    # if message.reference:
    #     if message.reference.resolved:
    #         ref = message.reference.resolved
    #         if isinstance(ref, discord.Message):
    #             message_content += f"\n\n[Ответ на сообщение:] {ref.jump_url}"
    #         elif isinstance(ref, discord.DeletedReferencedMessage):
    #             message_content += f"\n\n[Ответ на удалённое сообщение]: {ref.id}"

    if message.content:
        cleaned = await clean_message_text(bot, message)
        if cleaned:
            message_content += cleaned

    if message.stickers:
        message_content += "\n\n[Стикеры:]"
        for sticker in message.stickers:
            message_content += f"\n{sticker.name} ({sticker.id})\n"

    if message.attachments:
        message_content += "\n\n[Вложения:]"
        for attachment in message.attachments:
            message_content += f"\n{attachment.filename.replace('.', ' ')}\n"

    if message.embeds:
        message_content += "\n\n[Ембеды:]"
        for embed in message.embeds:
            if embed.title:
                message_content += f"\nЗаголовок: {embed.title}"
            if embed.description:
                message_content += f"\nОписание: {embed.description}"

    if message.activity:
        activity_dict = await activity_to_dict(message.activity)
        message_content += f"\n\n[Активность из сообщения:]\n{await format_dict_fields(activity_dict)}"

        if message.author.activities:
            message_content += "\n\n[Все активности пользователя:]"
            for idx, activity in enumerate(message.author.activities, 1):
                activity_dict = await activity_to_dict(activity)
                activity_type = type(activity).__name__
                message_content += f"\n\n--- Активность {idx} ({activity_type}) ---\n{await format_dict_fields(activity_dict)}"

    if message.poll:
        poll_options = " | ".join([f'"{option.text}"' for option in message.poll.answers])
        message_content += (
            "\n\n[Опрос:]"
            f'\nВопрос: "{message.poll.question}"'
            f"\nОпции: {poll_options}"
        )

    message_content = message_content.strip()

    return message_content