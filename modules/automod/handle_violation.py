import asyncio
import hashlib
import time
import typing

from aiocache import SimpleMemoryCache
from datetime import timedelta
import discord

from classes.bot import LittleAngelBot
from modules.configuration import CONFIG
from modules.lock_manager import LockManagerWithIdleTTL

HIT_CACHE             = SimpleMemoryCache()
SENT_MESSAGES_CACHE   = SimpleMemoryCache()
VIOLATION_CACHE       = SimpleMemoryCache()  # guild_id -> List[timestamps]
INVITE_LOCKDOWN_CACHE = SimpleMemoryCache()

_PURGE_SEMAPHORE = asyncio.Semaphore(1)

LOCK_MANAGER_FOR_HITS     = LockManagerWithIdleTTL(idle_ttl=3600)
LOCK_MANAGER_FOR_MESSAGES = LockManagerWithIdleTTL(idle_ttl=2400)
LOCK_MANAGER_FOR_GUILD    = LockManagerWithIdleTTL(idle_ttl=7200)

INVITE_LOCKDOWN_DURATION = 2 * 60 * 60      # 2 часа
INVITE_LOCKDOWN_COOLDOWN = 45 * 60          # 45 минут
VIOLATION_WINDOW         = 5 * 60           # 5 минут
VIOLATION_LIMIT          = 10               # 10 нарушений в VILOATION_WINDOW минут

async def apply_invite_lockdown(bot: LittleAngelBot, guild: discord.Guild):
    now = time.time()

    async with LOCK_MANAGER_FOR_GUILD.lock(guild.id):
        data = await INVITE_LOCKDOWN_CACHE.get(guild.id) or {}

        lockdown_until = data.get("lockdown_until", 0)
        cooldown_until = data.get("cooldown_until", 0)

        # cooldown на продление
        if now < cooldown_until:
            return

        # если локдаун уже активен — ПРОДЛЕВАЕМ
        if now < lockdown_until:
            lockdown_until += INVITE_LOCKDOWN_DURATION
        else:
            lockdown_until = now + INVITE_LOCKDOWN_DURATION

            await safe_send_to_log(
                bot,
                content="🔒 **Включён локдаун приглашений и личных сообщений** на 2 часа вследствие всплеска нарушений"
            )

        disabled_until = discord.utils.utcnow() + timedelta(
            seconds=(lockdown_until - now)
        )

        await guild.edit(invites_disabled_until=disabled_until, dms_disabled_until=disabled_until)

        cooldown_until = now + INVITE_LOCKDOWN_COOLDOWN

        await INVITE_LOCKDOWN_CACHE.set(
            guild.id,
            {
                "lockdown_until": lockdown_until,
                "cooldown_until": cooldown_until
            },
            ttl=INVITE_LOCKDOWN_DURATION + INVITE_LOCKDOWN_COOLDOWN
        )

def generate_message_hash(message_content: str) -> str:
    """Генерирует хэш для идентификации типа нарушения"""
    return hashlib.md5(message_content.encode()).hexdigest()[:16]

async def check_message_sent_recently(user_id: int, message_hash: str) -> bool:
    """Проверяет, отправлялось ли недавно такое же сообщение в отношении данного пользователя"""
    async with LOCK_MANAGER_FOR_MESSAGES.lock(user_id):
        last_sent_cache: typing.List = await SENT_MESSAGES_CACHE.get(user_id)
        
        # Инициализация списка
        if last_sent_cache is None:
            last_sent_cache = []
        
        if message_hash in last_sent_cache:
            return True
        
        # Добавляет новый хэш и ограничивает размер списка
        last_sent_cache.append(message_hash)
        if len(last_sent_cache) > 10:  # Хранит только последние 10 типов нарушений
            last_sent_cache = last_sent_cache[-10:]
        
        await SENT_MESSAGES_CACHE.set(user_id, last_sent_cache, ttl=60)  # автоочистка через минуту
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
        channel: discord.TextChannel = bot.get_channel(CONFIG.AUTOMOD_LOGS_CHANNEL_ID)
        if not channel:
            channel: discord.TextChannel = await bot.fetch_channel(CONFIG.AUTOMOD_LOGS_CHANNEL_ID)
        return await channel.send(*args, **kwargs)
    except Exception:
        return None

async def safe_delete(msg: discord.Message):
    try: 
        await msg.delete()
    except Exception:
        pass

async def delete_messages_safe(
    channel: typing.Union[discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel],
    message_ids: set[int],
    reason: str = "Автоматическая очистка"
):
    """
    Безопасное удаление группы сообщений:
    - Пытается удалить с помощью bulk delete
    - Если не получилось - удаляет по одному, управляя скоростью
    """

    if not message_ids:
        return

    # --- основной безопасный purge ---
    async with _PURGE_SEMAPHORE:
        try:
            await channel.purge(
                check=lambda m: m.id in message_ids,
                bulk=True,
                limit=200,
                reason=reason
            )
            return
        except discord.HTTPException:
            # попадает в rate-limit, fallback
            pass

    # --- fallback: удаляет поштучно ---
    for msg_id in message_ids:

        try:
            await channel.delete_messages(
                [
                    discord.Object(id=msg_id)
                ]
            )
        except discord.NotFound:
            # попадает в not found - пропускает
            continue
        except discord.HTTPException:
            # ловит ошибку 429 - ждёт и пробует дальше
            await asyncio.sleep(2)
        finally:
            # минимальная задержка между удалениями
            await asyncio.sleep(0.25)

async def safe_timeout(member: discord.Member, duration: timedelta, reason: str = None):
    try:
        await member.timeout(duration, reason=reason)
    except Exception:
        pass

async def handle_violation(
    bot: LittleAngelBot,
    detected_member: discord.Member,
    detected_channel: typing.Union[discord.abc.GuildChannel, discord.Thread],
    detected_guild: discord.Guild,
    reason_title: str,
    reason_text: str,
    extra_info: str = "",
    detected_message: discord.Message = None,
    timeout_reason: str = None,
    force_mute: bool = False,
    force_ban: bool = False,
):

    now = time.time()

    async with LOCK_MANAGER_FOR_GUILD.lock(detected_guild.id):
        violations = await VIOLATION_CACHE.get(detected_guild.id) or []

        # скользящее окно
        violations = [t for t in violations if now - t <= VIOLATION_WINDOW]
        violations.append(now)

        await VIOLATION_CACHE.set(
            detected_guild.id,
            violations,
            ttl=VIOLATION_WINDOW
        )

        if len(violations) >= VIOLATION_LIMIT:
            asyncio.create_task(apply_invite_lockdown(bot, detected_guild))

    # Игнорирует системные сообщения (не выдаёт мут, а лишь удаляет сообщение)
    if detected_message and detected_message.is_system():
        await safe_delete(detected_message)
        return

    # hit-cache
    async with LOCK_MANAGER_FOR_HITS.lock(detected_member.id):
        hits = await HIT_CACHE.get(detected_member.id) or 0
        hits += 1
        await HIT_CACHE.set(detected_member.id, hits, ttl=3600)

    is_soft = hits <= 2 and not force_mute and not force_ban

    # LOG EMBED
    if force_ban:
        punishment = "Тебе выдан бан"
        action_text = f"Участнику {detected_member.mention} (`@{detected_member}`) был выдан бан"
    elif is_soft:
        punishment = "Наказание не применяется, за исключением удаления сообщения"
        action_text = f"Удалено сообщение от {detected_member.mention} (`@{detected_member}`)"
    else:
        punishment = "Тебе выдан мут на 1 час"
        action_text = f"Участнику {detected_member.mention} (`@{detected_member}`) был выдан мут на 1 час"

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
    log_embed.set_author(name=detected_guild.name, icon_url=detected_guild.icon.url if detected_guild.icon else None)
    log_embed.set_footer(text=f"ID: {detected_member.id}")
    log_embed.set_thumbnail(url=detected_member.display_avatar.url)
    log_embed.add_field(
        name="Канал:",
        value=f"{detected_channel.mention} (`#{detected_channel.name}`)",
        inline=False
    )

    asyncio.create_task(safe_send_to_log(bot, embed=log_embed, user_id=detected_member.id, message_content=log_desc))

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
    mention_embed.set_author(name=detected_guild.name, icon_url=detected_guild.icon.url if detected_guild.icon else None)
    mention_embed.set_thumbnail(url=detected_member.display_avatar.url)
    mention_embed.set_footer(
        text=(
            "Если ты считаешь, что это ошибка, проигнорируй это сообщение" 
            if is_soft and not force_ban 
            else "Если ты считаешь, что это ошибка, обратись к модераторам"
        )
    )

    asyncio.create_task(
            safe_send_to_channel(
            detected_member,
            embed=mention_embed,
            user_id=detected_member.id,
            message_content=f"[ЛИЧНЫЕ СООБЩЕНИЯ]\n\n{mention_desc}"
        )
    )

    if not isinstance(detected_channel, discord.ForumChannel):
        asyncio.create_task(
            safe_send_to_channel(
                detected_channel,
                content=detected_member.mention,
                embed=mention_embed,
                user_id=detected_member.id,
                message_content=mention_desc
            )
        )

    if detected_message and not force_ban:
        asyncio.create_task(safe_delete(detected_message))

    # выдаёт бан
    if force_ban:
        await safe_ban(detected_guild, detected_member, timeout_reason, delete_message_seconds=216000)
        await HIT_CACHE.delete(detected_member.id)

    # выдаёт мут
    elif not is_soft:
        await safe_timeout(detected_member, timedelta(hours=1), timeout_reason)
        await HIT_CACHE.delete(detected_member.id)