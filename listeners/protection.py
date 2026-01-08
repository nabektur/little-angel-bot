import time
import typing
import logging
import asyncio
import discord

from discord.ext                      import commands, tasks
from datetime                         import timedelta, datetime, timezone
from collections                      import defaultdict, deque

from modules.configuration            import config
from classes.bot                      import LittleAngelBot

from modules.automod.flood_filter     import flood_and_messages_check, messages_from_new_members_cache
from modules.automod.spam_filter      import is_spam_block
from modules.automod.link_filter      import detect_links
from modules.automod.handle_violation import handle_violation, safe_ban, safe_send_to_log
from modules.automod.thread_filter    import flood_and_threads_check, threads_from_new_members_cache
from modules.automod.mention_filter   import check_mention_abuse, mentions_from_new_members_cache

class AutoModeration(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

        self._channel_activity = defaultdict(lambda: deque())
        self._channel_locks    = defaultdict(asyncio.Lock)

        self.SLOWMODE_LEVELS = [
            (40, 30, 600),  # >=40 сообщений → 30s, hold 10 минут
            (30, 15, 300),  # >=30 сообщений → 15s, hold 5 минут
            (15, 3, 120),   # >=15 сообщений → 3s,  hold 2 минуты
        ]
        self._slowmode_state = {}
        self.WINDOW    = 10      # секунд

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._slowmode_task.is_running():
            self._slowmode_task.start()

    @tasks.loop(seconds=5)
    async def _slowmode_task(self):
        now = time.time()

        for channel_id, times in list(self._channel_activity.items()):
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            async with self._channel_locks[channel_id]:
                # чистим окно активности
                while times and now - times[0] > self.WINDOW:
                    times.popleft()

                count = len(times)
                current_delay = channel.slowmode_delay

                # определяем целевой delay
                target_delay = 0
                for limit, delay, _ in self.SLOWMODE_LEVELS:
                    if count >= limit:
                        target_delay = delay
                        break

                last_state = self._slowmode_state.get(channel_id)

                # усиление — сразу
                if target_delay > current_delay:
                    try:
                        await channel.edit(slowmode_delay=target_delay, reason="Ужесточение замедления в виду увеличения активности")
                        self._slowmode_state[channel_id] = (target_delay, now)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    continue

                # ослабление — только после hold текущего уровня
                if current_delay > target_delay and last_state:
                    last_delay, since = last_state

                    if last_delay != current_delay:
                        self._slowmode_state[channel_id] = (current_delay, now)
                        continue

                    hold_time = next(
                        (h for _, d, h in self.SLOWMODE_LEVELS if d == last_delay),
                        120
                    )

                    if now - since < hold_time:
                        continue

                    # находим следующий меньший уровень
                    lower_levels = [
                        d for _, d, _ in self.SLOWMODE_LEVELS
                        if d < last_delay
                    ]

                    next_delay = max(
                        (d for d in lower_levels if d >= target_delay),
                        default=target_delay
                    )

                    try:
                        await channel.edit(slowmode_delay=next_delay, reason="Смягчение замедления в виду уменьшения активности")
                        if next_delay > 0:
                            self._slowmode_state[channel_id] = (next_delay, now)
                        else:
                            self._slowmode_state.pop(channel_id, None)
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                # === очистка ===
                if not times and channel.slowmode_delay == 0:
                    self._channel_activity.pop(channel_id, None)
                    self._channel_locks.pop(channel_id, None)
                    self._slowmode_state.pop(channel_id, None)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):

        # базовые проверки
        if thread.guild.id != config.GUILD_ID:
            return
        if not thread.owner:
            return
        if thread.owner == self.bot.user:
            return
        if thread.owner.bot:
            return
        
        # расстановка приоритетов
        priority: int = 2

        if thread.owner.guild_permissions.manage_messages:
            priority = 0
        else:
            now = datetime.now(timezone.utc)

            if thread.owner.joined_at:
                difference_between_join_and_now = now - thread.owner.joined_at

                if difference_between_join_and_now > timedelta(weeks=2):
                    priority = 1
                elif difference_between_join_and_now < timedelta(days=2):
                    priority = 3

        if priority == 0:
            return
        
        # условия срабатывания
        if priority > 1:

            # модерация создания веток
            need_to_prune, matched, thread_name = await flood_and_threads_check(thread.owner, thread)

            if need_to_prune:

                extra = f"Название ветки:\n```\n#{thread_name}```"

                if not matched:
                    await handle_violation(
                        self.bot,
                        thread,
                        reason_title="Флуд ветками",
                        reason_text="флуд путём создания веток",
                        extra_info=extra,
                        timeout_reason="Флуд ветками",
                        force_ban=True
                    )

                else:

                    extra = f"Совпадение:\n```\n{matched}\n```\n{extra}"

                    await handle_violation(
                        self.bot,
                        thread,
                        reason_title="Реклама в названии ветки",
                        reason_text="реклама путём создания веток",
                        extra_info=extra,
                        timeout_reason="Реклама в названии ветки",
                        force_ban=True
                    )

                await threads_from_new_members_cache.delete(thread.owner.id)

                return


    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message):
        if message_before.content == message_after.content:
            return

        await self.on_message(message_after)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # базовые проверки
        if not message.guild:
            return
        if message.guild.id != config.GUILD_ID:
            return
        if message.author == self.bot.user:
            return
        if message.author.bot:
            if not message.interaction_metadata:
                return
            if message.interaction_metadata.is_guild_integration():
                return
            message.author = message.interaction_metadata.user
        
        # расстановка приоритетов
        priority: int = 2

        if message.author.guild_permissions.manage_messages:
            priority = 0
        elif message.interaction_metadata:
            priority = 3
        elif message.channel.id in config.ADS_CHANNELS_IDS:
            priority = 0
        else:
            now = datetime.now(timezone.utc)

            if message.author.joined_at:
                difference_between_join_and_now = now - message.author.joined_at

                if difference_between_join_and_now > timedelta(weeks=2):
                    priority = 1
                elif difference_between_join_and_now < timedelta(days=2):
                    priority = 3

        if priority == 0:
            return

        # ===== Авто slow mode (нагрузка на канал) =====
        if isinstance(message.channel, discord.TextChannel):
            now = time.time()
            channel_id = message.channel.id

            async with self._channel_locks[channel_id]:
                times = self._channel_activity[channel_id]
                times.append(now)

                # лёгкая чистка, основная в таске
                while times and now - times[0] > self.WINDOW:
                    times.popleft()
                
        # условия срабатывания
        if priority > 2:

            if message.content:
                # детект злоупотребления упоминаниями
                is_mention_abuse, mention_content = await check_mention_abuse(message.author, message)

                if is_mention_abuse:

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Злоупотребление упоминаниями",
                        reason_text="злоупотребление упоминаниями",
                        extra_info=f"Содержание сообщения (первые 300 символов):\n```\n{mention_content[:300].replace('`', '')}\n```",
                        timeout_reason="Злоупотребление упоминаниями от нового участника",
                        force_mute=True
                    )

                    await mentions_from_new_members_cache.delete(message.author.id)

                    return

            # детект флуда
            is_flood, flood_content = await flood_and_messages_check(self.bot, message.author, message)

            if is_flood:

                await handle_violation(
                    self.bot,
                    message,
                    reason_title="Флуд",
                    reason_text="флуд",
                    extra_info=f"Содержание сообщения (первые 300 символов):\n```\n{flood_content[:300].replace('`', '')}\n```",
                    timeout_reason="Флуд от нового участника",
                    force_mute=True
                )

                await messages_from_new_members_cache.delete(message.author.id)

                return
                
        # условия срабатывания
        if priority > 1:
                
            # модерация активности
            if message.activity is not None:

                if message.activity.get('type') == 3:

                    activity_info = (
                        f"Тип: {message.activity.get('type')}\n"
                        f"Party ID: {message.activity.get('party_id')}\n"
                    )

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Реклама через активность",
                        reason_text="реклама через Discord Activity",
                        extra_info=f"Информация об активности:\n```\n{activity_info}```",
                        timeout_reason="Реклама через активность"
                    )

                    return
            
            # модерация сообщений
            if message.content or message.embeds:
            
                # защита от засирания чата

                message_content = message.content if message.content else ""
                for embed in message.embeds:
                    if embed.title:
                        message_content += f"\nЗаголовок: {embed.title}"
                    if embed.description:
                        message_content += f"\nОписание: {embed.description}"

                if await is_spam_block(message_content):

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Спам / засорение чата",
                        reason_text="засорение чата (пустые строки / мусор / код-блоки)",
                        extra_info=f"Содержание сообщения (первые 300 символов):\n```\n{message_content[:300].replace('`', '')}\n```",
                        timeout_reason="Спам / засорение чата"
                    )

                    return

                # детект рекламы

                matched = await detect_links(message.content)

                if matched:

                    # первые 300 символов сообщения
                    preview = message.content[:300].replace("`", "'")

                    extra = (
                        f"Совпадение:\n```\n{matched}\n```\n"
                        f"Содержание сообщения (первые 300 символов):\n```\n{preview}\n```"
                    )

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Реклама в сообщении",
                        reason_text="реклама в тексте сообщения",
                        extra_info=extra,
                        timeout_reason="Реклама в сообщении"
                    )

                    return
                
        # условия срабатывания
        if priority > 0:

            # модерация вложенных файлов
            if message.attachments:

                for attachment in message.attachments:

                    if not attachment.content_type:
                        continue

                    # Проверяет только текстовые файлы
                    if attachment.content_type and any(ct in attachment.content_type for ct in [
                        "text/", "application/json", "application/xml", 
                        "application/x-yaml", "application/yaml"
                    ]):

                        # ограничение по размеру
                        # if attachment.size > MAX_FILE_SIZE_BYTES:
                        #     continue

                        try:
                            file_bytes = await asyncio.wait_for(attachment.read(), timeout=30)
                        except (asyncio.TimeoutError, discord.HTTPException):
                            continue

                        if file_bytes.count(b"\x00") > 100:
                            continue  # бинарный файл

                        content = file_bytes[:1_000_000].decode(errors='ignore')

                        matched = await detect_links(content)

                        if matched:

                            # первые 300 символов файла
                            preview = content[:300].replace("`", "'")

                            file_info = (
                                f"Имя файла: {attachment.filename}\n"
                                f"Размер: {attachment.size} байт\n"
                                f"Тип: {attachment.content_type}\n"
                            )

                            extra = (
                                f"Совпадение:\n```\n{matched}\n```\n"
                                f"Информация о файле:\n```\n{file_info}```\n"
                                f"Содержание сообщения (первые 300 символов):\n```\n{preview}\n```"
                            )

                            await handle_violation(
                                self.bot,
                                message,
                                reason_title="Реклама внутри файла",
                                reason_text="реклама в прикреплённом файле",
                                extra_info=extra,
                                timeout_reason="Реклама в файле",
                                force_ban=True
                            )

                            return
                    
            # модерация опросов
            if message.poll:

                poll_options = " | ".join([f'"{option.text}"' for option in message.poll.answers])
                poll_content = (
                    "\n\n[Опрос:]"
                    f'\nВопрос: "{message.poll.question}"'
                    f"\nОпции: {poll_options}"
                )

                matched = await detect_links(poll_content)

                if matched:

                    extra = (
                        f"Совпадение:\n```\n{matched}\n```\n"
                        f"Информация об опросе:\n```\n{poll_content}```\n"
                    )

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Реклама внутри опроса",
                        reason_text="реклама в прикреплённом опросе",
                        extra_info=extra,
                        timeout_reason="Реклама в опросе",
                        force_ban=True
                    )

                    return

                
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        if guild.id != config.GUILD_ID:
            return

        if channel.id not in config.PROTECTED_CHANNELS_IDS:
            return

        # Ищет кто удалил канал
        await asyncio.sleep(1)

        who_deleted: typing.List[typing.Union[discord.User, discord.Member]] = []

        try:
            async for entry in guild.audit_logs(limit=15, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    if entry.user.id != self.bot.user.id:
                        who_deleted.append(entry.user)
                    break
        except:
            pass

        # Если удалил бот -> ищет кто добавил бота (в течение 3 дней)
        resolved: typing.List[typing.Union[discord.User, discord.Member]] = []

        for user in who_deleted:
            resolved.append(user)
            if user.bot:
                try:
                    async for entry in guild.audit_logs(
                        limit=10,
                        action=discord.AuditLogAction.bot_add,
                        after=datetime.now(timezone.utc) - timedelta(days=3)
                    ):
                        if entry.target.id == user.id:
                            resolved.append(entry.user)
                            break
                except:
                    pass

        # Никого не нашёл -> предупреждение о подозрении на краш
        if not resolved:
            embed = discord.Embed(
                title="Удаление защищённого канала",
                description=(
                    f"Защищённый канал `#{channel.name}` ({channel.id}) был удалён, но не удалось определить, кем именно\n"
                    f"Возможная причина: попытка краша сервера"
                ),
                color=0xFF0000
            )
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
            embed.set_footer(text="Удаливший не найден")
            embed.add_field(name="Канал:", value=f"`#{channel.name}` (`{channel.id}`)")

            return await safe_send_to_log(self.bot, embed=embed)

        # Находит всех + банит каждого
        embeds = []

        for i, user in enumerate(resolved, 1):
            reason = f"Удаление защищённого канала #{channel.name} ({channel.id})"

            embed = discord.Embed(
                title="Удаление защищённого канала",
                description=(
                    f"{user.mention} (`@{user}`) был забанен.\n"
                    f"Причина: удаление защищённого канала `#{channel.name}` (`{channel.id}`)\n"
                    f"Возможная причина: попытка краша сервера"
                ),
                color=0xFF0000,
            )
            embed.set_footer(text=f"ID: {user.id}")
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Канал:", value=f"`#{channel.name}` (`{channel.id}`)")

            if i == 1:
                embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

            embeds.append(embed)

            await safe_ban(guild, user, reason=reason)

        await safe_send_to_log(self.bot, embeds=embeds)

async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoModeration(bot))