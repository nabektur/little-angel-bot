import typing
import logging
import discord
import asyncio
import traceback

from aiocache                    import SimpleMemoryCache
from cache                       import AsyncTTL

from modules.automod.link_filter import detect_links

threads_from_new_members_cache = SimpleMemoryCache()

_DELETE_SEMAPHORE = asyncio.Semaphore(1)

# Settings
MAX_THREADS = 7  # максимальное количество веток в кэше

@AsyncTTL(time_to_live=2400)
async def get_lock(user_id: int) -> asyncio.Lock:
    return asyncio.Lock()

async def update_thread_system_message(member: discord.Member, system_message: discord.Message) -> None:
    async with await get_lock(member.id):
        threads = await threads_from_new_members_cache.get(member.id) or []

        threads = threads[-MAX_THREADS:]

        for thread in threads:
            if thread["name"] == system_message.content:
                thread["system_message_id"] = system_message.id

        await threads_from_new_members_cache.set(member.id, threads, ttl=1200)

async def get_cached_threads_and_append(member: discord.Member, append_thread: discord.Thread) -> list:
    async with await get_lock(member.id):
        threads = await threads_from_new_members_cache.get(member.id) or []

        threads = threads[-MAX_THREADS:]

        if append_thread:
            threads.append({
                "id": append_thread.id,
                "name": append_thread.name,
                "system_message_id": None
            })

            await threads_from_new_members_cache.set(member.id, threads, ttl=1200)


    return threads

async def analyze_thread(member: discord.Member, thread: discord.Thread) -> typing.Tuple[bool, list, typing.Optional[str]]:
    """
    Возвращает булевое значение: True — если обнаружен флуд, False — если нет.
    """

    # Сохранение ветки в кэш + получение полного списка веток
    threads_list = await get_cached_threads_and_append(member, append_thread=thread)

    # --- Проверка гарантированного флуда ---
    # Нужно MAX_THREADS тредов, чтобы определить повтор
    if len(threads_list) >= MAX_THREADS:
        return True, threads_list, None
    
    matched = await detect_links(thread.name)

    if matched:
        return True, threads_list, matched
    
    return False, threads_list, matched

async def delete_thread_safe(
    thread: discord.Thread,
    system_message_id: int = None,
    reason: str = "Автоматическая очистка"
):
    """
    Безопасное удаление ветки
    """

    # --- основной безопасный delete ---
    async with _DELETE_SEMAPHORE:

        if system_message_id and thread.parent and not isinstance(thread.parent, discord.ForumChannel):
            try:
                await thread.parent.delete_messages(
                    [discord.abc.Snowflake(system_message_id)]
                )
            except (discord.HTTPException, discord.NotFound):
                # попадает в rate-limit, попадает в not found, fallback
                pass

        try:
            await thread.delete(
                reason=reason
            )
            return
        except discord.HTTPException:
            # попадает в rate-limit, fallback
            pass


async def flood_and_threads_check(member: discord.Member, thread: discord.Thread) -> typing.Tuple[bool, typing.Optional[str], str]:
    is_flood, threads, matched = await analyze_thread(member, thread)

    if is_flood:
        
        for th_dict in threads:

            try:
                th = member.guild.get_thread(th_dict["id"]) or await member.guild.fetch_channel(th_dict["id"])
                if not isinstance(th, discord.Thread):
                    continue
                
                asyncio.create_task(delete_thread_safe(th, th_dict.get("system_message_id"), reason="Реклама в ветке" if matched else "Флуд ветками от нового участника"))

            except Exception:
                logging.error(traceback.format_exc())
                pass

    return is_flood, matched, thread.name