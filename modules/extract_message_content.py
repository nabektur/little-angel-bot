from cache import AsyncTTL
import discord
from discord.ext.commands import clean_content

from classes.bot import LittleAngelBot

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
            message_content += f"\n{attachment.filename}"

    if message.embeds:
        message_content += "\n\n[Ембеды:]"
        for embed in message.embeds:
            if embed.title:
                message_content += f"\nЗаголовок: {embed.title}"
            if embed.description:
                message_content += f"\nОписание: {embed.description}"

    if message.activity:
        message_content += (
            "\n\n[Активность:]"
            f"\nТип: {message.activity.get('type')}"
            f"\nParty ID: {message.activity.get('party_id', 'N/A')}"
        )
        if message.activity.get('type') == 3:
            activity_presence = None
            for presence in message.author.activities:
                if isinstance(presence, discord.Spotify):
                    activity_presence = presence
                    break

            message_content += (
                f"\nТрек: {activity_presence.title if hasattr(activity_presence, 'title') else 'Нет трека'}"
                f"\nURL трека: {activity_presence.track_url if hasattr(activity_presence, 'track_url') else 'Нет ссылки'}"
                f"\nАльбом: {activity_presence.album if hasattr(activity_presence, 'album') else 'Нет альбома'}"
                f"\nИсполнитель: {activity_presence.artist if hasattr(activity_presence, 'artist') else 'Нет исполнителя'}"
            )

    if message.poll:
        poll_options = " | ".join([f'"{option.text}"' for option in message.poll.answers])
        message_content += (
            "\n\n[Опрос:]"
            f'\nВопрос: "{message.poll.question}"'
            f"\nОпции: {poll_options}"
        )

    message_content = message_content.strip()

    return message_content

