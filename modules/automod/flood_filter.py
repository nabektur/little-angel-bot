import asyncio
from collections import defaultdict
import logging
import traceback
import typing

from aiocache import SimpleMemoryCache
from cache import AsyncTTL
import discord
from discord.ext.commands import clean_content
from rapidfuzz import fuzz

from classes.bot import LittleAngelBot
from modules.automod.handle_violation import delete_messages_safe
from modules.lock_manager import LockManagerWithIdleTTL

MESSAGES_FROM_NEW_MEMBERS_CACHE = SimpleMemoryCache()
LOCK_MANAGER = LockManagerWithIdleTTL(idle_ttl=2400)

MAX_CACHE_MESSAGES = 60  # максимальное количество сообщений в кэше
GUARANTEED_WINDOW = 15  # количество сообщений для гарантированного флуда
ALTERNATING_WINDOW = 60  # окно анализа для чередования
FUZZY_THRESHOLD = 80  # порог нечёткого сравнения в процентах
MIN_CLUSTERS_FOR_ALTERNATING = 2  # количество кластеров для засчитывания флуда как чередование
MIN_CLUSTER_SIZE = 15  # количество сообщений в кластере для засчитывания флуда как чередование

@AsyncTTL(time_to_live=1600, maxsize=20000)
async def fuzzy_compare(str1: str, str2: str) -> int:
    try:
        score = fuzz.ratio(str1, str2)
    except Exception:
        score = 0
    return score

async def get_cached_messages_and_append(member: discord.Member, append_message_content: str = None, append_message: discord.Message = None) -> list:
    async with LOCK_MANAGER.lock(member.id):
        messages = await MESSAGES_FROM_NEW_MEMBERS_CACHE.get(member.id) or []

        messages = messages[-MAX_CACHE_MESSAGES:]  # ограничение кэша до MAX_CACHE_MESSAGES

        if append_message_content:

            # Удаляет предыдущее сообщение с таким же id
            messages = [m for m in messages if m.get("id") != append_message.id]

            messages.append({
                "content": append_message_content,
                "id": append_message.id,
                "channel_id": append_message.channel.id
            })

            await MESSAGES_FROM_NEW_MEMBERS_CACHE.set(member.id, messages, ttl=1200)


    return messages

async def clean_message_text(bot: LittleAngelBot, message: discord.Message):
    cleaner = clean_content(
        fix_channel_mentions=True,
        use_nicknames=True,
        escape_markdown=True
    )

    ctx = await bot.get_context(message)

    cleaned = await cleaner.convert(ctx, message.content)
    return cleaned

async def append_cached_messages(bot: LittleAngelBot, member: discord.Member, message: discord.Message) -> str:

    message_content = ""

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

    # if message.reference:
    #     if message.reference.resolved:
    #         ref = message.reference.resolved
    #         if isinstance(ref, discord.Message):
    #             message_content += f"\n\n[Ответ на сообщение:] {ref.jump_url}"
    #         elif isinstance(ref, discord.DeletedReferencedMessage):
    #             message_content += f"\n\n[Ответ на удалённое сообщение]: {ref.id}"

    if message.activity:
        message_content += (
            "\n\n[Активность:]"
            f"\nТип: {message.activity.get('type')}"
            f"\nParty ID: {message.activity.get('party_id')}"
        )

    if message.poll:
        poll_options = " | ".join([f'"{option.text}"' for option in message.poll.answers])
        message_content += (
            "\n\n[Опрос:]"
            f'\nВопрос: "{message.poll.question}"'
            f"\nОпции: {poll_options}"
        )

    message_content = message_content.strip()

    messages = await get_cached_messages_and_append(member, append_message_content=message_content, append_message=message)

    return message_content, messages

async def detect_flood(bot: LittleAngelBot, member: discord.Member, message: discord.Message) -> typing.Tuple[bool, list, str]:
    """
    Возвращает булевое значение: True - если обнаружен флуд, False - если нет.
    """

    # Сохранение сообщения в кэш + получение полного текста
    message_content, message_list = await append_cached_messages(bot, member, message)

    # --- Подготовка окон ---
    guaranteed_slice = message_list[-(GUARANTEED_WINDOW + 20):]
    alternating_slice = message_list[-ALTERNATING_WINDOW:]

    result = {
        "detected": False,
        "guaranteed_flood": False,
        "alternating_flood": False,
        "alternating_clusters_count": 0,
        "details": {
            "guaranteed_checked": len(guaranteed_slice),
            "alternating_checked": len(alternating_slice),
            "clusters": []
        }
    }

    # --- Проверка гарантированного флуда ---
    # Нужно как минимум GUARANTEED_WINDOW сообщений, чтобы определить повтор
    if len(guaranteed_slice) >= GUARANTEED_WINDOW:

        guaranteed_clusters = []

        # Кластеризация указанного количества сообщений
        for i, msg in enumerate(guaranteed_slice):
            cur = (msg["content"] or "").strip()
            if not cur:
                continue

            placed = False

            for cl in guaranteed_clusters:
                proto = cl["prototype"]

                # Прямое сравнение
                if cur == proto:
                    cl["count"] += 1
                    cl["indices"].append(i)
                    placed = True
                    break

                # Нечёткое сравнение
                sim = await fuzzy_compare(cur, proto)
                if sim >= FUZZY_THRESHOLD:
                    cl["count"] += 1
                    cl["indices"].append(i)
                    placed = True
                    break

            if not placed:
                guaranteed_clusters.append({
                    "prototype": cur,
                    "count": 1,
                    "indices": [i]
                })

        # Если есть кластер из указанного количества сообщений - гарантированный флуд
        for cl in guaranteed_clusters:
            if cl["count"] >= GUARANTEED_WINDOW:
                result["detected"] = True
                result["guaranteed_flood"] = True
                return True, message_list, message_content

    # --- Проверка на чередование / повторяющиеся кластеры (не гарантированный флуд) ---
    # Создаёт кластеры: каждый новый текст сравнивается с существующими прототипами кластера.
    clusters = []  # список: [{"prototype": str, "indices": [i,...], "count": n}, ...]

    for i, msg in enumerate(alternating_slice):
        cur = (msg["content"] or "").strip()
        if not cur:
            continue

        placed = False
        # пробует присоединить к уже существующему кластеру
        for cl in clusters:
            proto = cl["prototype"]
            # быстрое прямое сравнение прежде нечёткого
            if cur == proto:
                cl["indices"].append(i)
                cl["count"] += 1
                placed = True
                break
            else:
                try:
                    sim = await fuzzy_compare(cur, proto)
                except Exception:
                    sim = 0
                if sim >= FUZZY_THRESHOLD:
                    cl["indices"].append(i)
                    cl["count"] += 1
                    placed = True
                    break

        if not placed:
            # создаётся новый кластер
            clusters.append({
                "prototype": cur,
                "indices": [i],
                "count": 1
            })

    # Подсчитается сколько кластеров имеют размер >= MIN_CLUSTER_SIZE
    repeating_clusters = [c for c in clusters if c["count"] >= MIN_CLUSTER_SIZE]
    result["alternating_clusters_count"] = len(repeating_clusters)
    result["details"]["clusters"] = [
        {"prototype": c["prototype"][:200], "count": c["count"], "indices": c["indices"]} for c in clusters
    ]

    if len(repeating_clusters) >= MIN_CLUSTERS_FOR_ALTERNATING:
        result["alternating_flood"] = True
        result["detected"] = True

        return True, message_list, message_content
    
    return False, message_list, message_content

async def flood_and_messages_check(bot: LittleAngelBot, member: discord.Member, message: discord.Message) -> typing.Tuple[bool, str]:
    is_flood, messages, message_content = await detect_flood(bot, member, message)

    if is_flood:
        
        try:
            messages_by_channel = defaultdict(set)

            for msg in messages:
                messages_by_channel[msg["channel_id"]].add(msg["id"])

            for channel_id, ids in messages_by_channel.items():
                try:
                    channel = member.guild.get_channel(channel_id) or await member.guild.fetch_channel(channel_id)
                    asyncio.create_task(delete_messages_safe(channel, ids, reason="Флуд от нового участника"))

                except Exception:
                    logging.error(traceback.format_exc())
                    pass

        except Exception:
            logging.error(traceback.format_exc())
            pass

    return is_flood, message_content