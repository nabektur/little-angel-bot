import discord

from aiocache import SimpleMemoryCache
from datetime import timedelta

from classes.bot           import LittleAngelBot
from modules.configuration import config

hit_cache = SimpleMemoryCache()

async def safe_ban(guild: discord.Guild, member: discord.abc.Snowflake, reason: str = None, delete_message_seconds: int = 0):
    try:
        await guild.ban(member, reason=reason, delete_message_seconds=delete_message_seconds)
    except Exception:
        pass

async def safe_send_to_channel(channel: discord.abc.Messageable, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except Exception:
        return None

async def safe_send_to_log(bot: LittleAngelBot, *args, **kwargs):
    try:
        channel: discord.TextChannel = bot.get_channel(config.AUTOMOD_LOGS_CHANNEL_ID)
        if not channel:
            channel: discord.TextChannel = await bot.fetch_channel(config.AUTOMOD_LOGS_CHANNEL_ID)
        return await channel.send(*args, **kwargs)
    except Exception:
        return None

async def safe_delete(msg: discord.Message):
    try: 
        await msg.delete()
    except Exception:
        pass

async def safe_timeout(member: discord.Member, duration: timedelta, reason: str):
    try:
        await member.timeout(duration, reason=reason)
    except Exception:
        pass

async def handle_violation(
    bot: LittleAngelBot,
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

    await safe_send_to_log(bot, embed=log_embed)

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

    await safe_send_to_channel(
        message.channel,
        content=user.mention,
        embed=mention_embed
    )

    await safe_delete(message)

    # выдаёт мут
    if not is_soft and timeout_reason:
        await safe_timeout(user, timedelta(hours=1), timeout_reason)
        await hit_cache.delete(user.id)