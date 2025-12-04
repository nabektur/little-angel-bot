import typing
import logging
import discord
import asyncio

from rapidfuzz import fuzz, process
from aiocache  import SimpleMemoryCache
from cache     import AsyncTTL

messages_from_new_members_cache = SimpleMemoryCache()

locks = {}

# Settings
MAX_CACHE_MESSAGES = 50
GUARANTEED_WINDOW = 6       # количество сообщений для гарантированного флуда
ALTERNATING_WINDOW = 15     # количество сообщений для засчитывания флуда как чередование
FUZZY_THRESHOLD = 80        # порог нечёткого сравнения в процентах
MIN_CLUSTERS_FOR_ALTERNATING = 3
MIN_CLUSTER_SIZE = 2

@AsyncTTL(time_to_live=600)
async def get_lock(user_id):
    return asyncio.Lock()

@AsyncTTL(time_to_live=600)
async def fuzzy_compare(str1: str, str2: str) -> int:
    try:
        score = fuzz.ratio(str1, str2)
    except Exception:
        score = 0
    return score

async def get_cached_messages_and_append(member: discord.Member, append_message_content: str = None, append_message: discord.Message = None) -> list:
    async with await get_lock(member.id):
        messages = await messages_from_new_members_cache.get(member.id) or []

        messages = messages[-MAX_CACHE_MESSAGES:]  # ограничение кэша до MAX_CACHE_MESSAGES

        if append_message_content:
            messages.append({
                "content": append_message_content,
                "id": append_message.id,
                "channel_id": append_message.channel.id
            })

            await messages_from_new_members_cache.set(member.id, messages, ttl=300)


    return messages

async def append_cached_messages(member: discord.Member, message: discord.Message) -> str:

    message_content = message.content or ""

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

    if message.reference:
        if message.reference.resolved:
            ref = message.reference.resolved
            if isinstance(ref, discord.Message):
                if ref.content:
                    message_content += f"\n\n[Ответ на сообщение:] {ref.jump_url}"
            elif isinstance(ref, discord.DeletedReferencedMessage):
                message_content += f"\n\n[Ответ на удалённое сообщение]: {ref.id}"

    messages = await get_cached_messages_and_append(member, append_message_content=message_content, append_message=message)

    return message_content, messages

async def detect_flood(member: discord.Member, channel: discord.TextChannel, message: discord.Message) -> typing.Tuple[bool, list]:
    """
    Возвращает булевое значение: True — если обнаружен флуд, False — если нет.
    """

    # Сохранение сообщения в кэш + получение полного текста
    message_content, message_list = await append_cached_messages(member, message)

    # --- Подготовка окон ---
    guaranteed_slice = message_list[-GUARANTEED_WINDOW:]
    alternating_slice = message_list[-ALTERNATING_WINDOW:] if len(message_list) >= 2 else message_list

    result = {
        "detected": False,
        "guaranteed_flood": False,
        "primary_match_count": 0,
        "alternating_flood": False,
        "alternating_clusters_count": 0,
        "details": {
            "guaranteed_checked": len(guaranteed_slice),
            "alternating_checked": len(alternating_slice),
            "clusters": []
        }
    }

    # --- Проверка гарантированного флуда ---
    # Нужны как минимум 6 сообщений, чтобы определить повтор
    if len(guaranteed_slice) >= GUARANTEED_WINDOW:

        guaranteed_clusters = []

        # Кластеризация последних 6 сообщений
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

        # Если есть кластер из 6 сообщений - гарантированный флуд
        for cl in guaranteed_clusters:
            if cl["count"] >= GUARANTEED_WINDOW:
                result["detected"] = True
                result["guaranteed_flood"] = True
                logging.info(
                    f"[FloodFilter] Гарантированный флуд обнаружен для участника "
                    f"{member.id} на сервере {channel.guild.id} в канале {channel.id}"
                )
                return True, message_list

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

        logging.info(f"[FloodFilter] Чередующийся флуд обнаружен для участника {member.id} на сервере {channel.guild.id} в канале {channel.id}")

        return True, message_list
    
    return False, message_list

async def flood_and_messages_check(member: discord.Member, channel: discord.TextChannel, message: discord.Message) -> bool:
    is_flood, messages = await detect_flood(member, channel, message)

    if is_flood:

        channels_for_purge = []
        messages_ids_for_purge = []
        
        for message in messages:

            if message["channel_id"] not in channels_for_purge:

                channel = member.guild.get_channel(message["channel_id"])
                if not channel:
                    try:
                        channel = await member.guild.fetch_channel(message["channel_id"])
                    except Exception:
                        continue
            
                channels_for_purge.append(channel)

            messages_ids_for_purge.append(message["id"])

        messages_ids_for_purge = set(messages_ids_for_purge)

        for channel in channels_for_purge:
            await channel.purge(check=lambda m: m.id in messages_ids_for_purge, reason="Флуд от нового участника", limit=100, bulk=True)
            await asyncio.sleep(0.5)

    return is_flood