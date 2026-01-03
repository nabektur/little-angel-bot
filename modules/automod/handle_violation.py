import typing
import asyncio
import discord
import hashlib

from aiocache              import SimpleMemoryCache
from datetime              import timedelta

from classes.bot           import LittleAngelBot
from modules.configuration import config
from modules.lock_manager  import LockManagerWithIdleTTL

hit_cache = SimpleMemoryCache()
sent_messages_cache = SimpleMemoryCache()
lock_manager = LockManagerWithIdleTTL(idle_ttl=2400)

def generate_message_hash(message_content: str) -> str:
    """Генерирует хэш для идентификации типа нарушения"""
    return hashlib.md5(message_content.encode()).hexdigest()[:16]

async def check_message_sent_recently(user_id: int, message_hash: str) -> bool:
    """Проверяет, отправлялось ли недавно такое же сообщение в отношении данного пользователя"""
    async with lock_manager.lock(user_id):
        last_sent_cache: typing.List = await sent_messages_cache.get(user_id)
        
        # Инициализация списка
        if last_sent_cache is None:
            last_sent_cache = []
        
        if message_hash in last_sent_cache:
            return True
        
        # Добавляет новый хэш и ограничивает размер списка
        last_sent_cache.append(message_hash)
        if len(last_sent_cache) > 10:  # Хранит только последние 10 типов нарушений
            last_sent_cache = last_sent_cache[-10:]
        
        await sent_messages_cache.set(user_id, last_sent_cache, ttl=300)  # 5 минут вместо 5 секунд
        return False

async def safe_ban(guild: discord.Guild, member: discord.abc.Snowflake, reason: str = None, delete_message_seconds: int = 0):
    try:
        await guild.ban(member, reason=reason, delete_message_seconds=delete_message_seconds)
    except Exception:
        pass

async def safe_send_to_channel(channel: discord.abc.Messageable, *args, user_id: int = None, message_content: str = None, **kwargs):
    if user_id and message_content and await check_message_sent_recently(user_id, generate_message_hash(message_content)):
        return None
    try:
        return await channel.send(*args, **kwargs)
    except Exception:
        return None

async def safe_send_to_log(bot: LittleAngelBot, *args, user_id: int = None, message_content: str = None, **kwargs):
    if user_id and message_content and await check_message_sent_recently(user_id, generate_message_hash(message_content)):
        return None
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

async def safe_timeout(member: discord.Member, duration: timedelta, reason: str = None):
    try:
        await member.timeout(duration, reason=reason)
    except Exception:
        pass

async def handle_violation(
    bot: LittleAngelBot,
    detected_object: typing.Union[discord.Message, discord.Thread],
    reason_title: str,
    reason_text: str,
    extra_info: str = "",
    timeout_reason: str = None,
    force_mute: bool = False,
    force_ban: bool = False,
):
    if isinstance(detected_object, discord.Message):
        user = detected_object.author
    else:
        user = detected_object.owner
    guild = detected_object.guild

    # Игнорирует системные сообщения (не выдаёт мут, а лишь удаляет сообщение)
    if isinstance(detected_object, discord.Message) and detected_object.is_system():
        await safe_delete(detected_object)
        return

    # hit-cache
    hits = await hit_cache.get(user.id) or 0
    hits += 1
    await hit_cache.set(user.id, hits, ttl=3600)

    is_soft = hits <= 2 and not force_mute and not force_ban
    # Хэш для идентификации типа нарушения
    detected_channel = detected_object.parent if isinstance(detected_object, discord.Thread) else detected_object.channel

    # LOG EMBED
    if force_ban:
        punishment = "Тебе выдан бан"
        action_text = f"Участнику {user.mention} (`@{user}`) был выдан бан"
    elif is_soft:
        punishment = "Наказание не применяется, за исключением удаления сообщения"
        action_text = f"Удалено сообщение от {user.mention} (`@{user}`)"
    else:
        punishment = "Тебе выдан мут на 1 час"
        action_text = f"Участнику {user.mention} (`@{user}`) был выдан мут на 1 час"

    log_desc = (
        f"{action_text}\n"
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
        value=f"{detected_channel.mention} (`#{detected_channel.name}`)",
        inline=False
    )

    asyncio.create_task(safe_send_to_log(bot, embed=log_embed, user_id=user.id, message_content=log_desc))

    # MENTION EMBED
    mention_desc = (
        f"Причина срабатывания: {reason_text}\n"
        f"{punishment}\n\n"
        # f"{extra_info}\n"
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
        text=(
            "Если ты считаешь, что это ошибка, проигнорируй это сообщение" 
            if is_soft and not force_ban 
            else "Если ты считаешь, что это ошибка, обратись к модераторам"
        )
    )

    asyncio.create_task(
            safe_send_to_channel(
            user,
            embed=mention_embed,
            user_id=user.id,
            message_content=f"[ЛИЧНЫЕ СООБЩЕНИЯ]\n\n{mention_desc}"
        )
    )

    if not isinstance(detected_channel, discord.ForumChannel):
        asyncio.create_task(
            safe_send_to_channel(
                detected_channel,
                content=user.mention,
                embed=mention_embed,
                user_id=user.id,
                message_content=mention_desc
            )
        )

    if isinstance(detected_object, discord.Message) and not force_ban:
        asyncio.create_task(safe_delete(detected_object))

    # выдаёт бан
    if force_ban:
        await safe_ban(guild, user, timeout_reason, delete_message_seconds=216000)
        await hit_cache.delete(user.id)

    # выдаёт мут
    elif not is_soft:
        await safe_timeout(user, timedelta(hours=1), timeout_reason)
        await hit_cache.delete(user.id)