import typing
import discord
import asyncio

from discord.ext import commands
from datetime    import timedelta, datetime, timezone

from modules.configuration import config
from classes.bot           import LittleAngelBot

from modules.automod.flood_filter     import flood_and_messages_check
from modules.automod.spam_filter      import is_spam_block
from modules.automod.link_filter      import detect_links
from modules.automod.handle_violation import handle_violation, safe_ban, safe_send_to_log

class AutoModeration(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # базовые проверки
        if message.author == self.bot.user:
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.guild.id != config.GUILD_ID:
            return
        
        # расстановка приоритетов
        priority: int = 2

        if message.channel.permissions_for(message.author).manage_messages:
            priority = 0
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

        # модерация активности

        if message.activity is not None:

            # условия срабатывания
            if priority > 1:

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
        if message.content:
                
                if priority > 2:

                    # детект флуда

                    is_flood = await flood_and_messages_check(message.author, message.channel, message)

                    if is_flood:

                        await handle_violation(
                            self.bot,
                            message,
                            reason_title="Флуд",
                            reason_text="флуд",
                            timeout_reason="Флуд",
                            force_harsh=True
                        )

                        return
                
                
                elif priority > 1:
                
                    # защита от засирания чата 

                    if await is_spam_block(message.content):

                        await handle_violation(
                            self.bot,
                            message,
                            reason_title="Спам / засорение чата",
                            reason_text="засорение чата (пустые строки / мусор / код-блоки)",
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
                            f"Первые 300 символов:\n```\n{preview}\n```"
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

        # модерация вложенных файлов

        if message.attachments and priority > 0:

            for attachment in message.attachments:

                if not attachment.content_type:
                    continue

                if not any(ct in attachment.content_type for ct in ["text", "json", "xml", "csv", "html", "htm", "md", "yaml", "yml", "ini", "log", "multipart", "text/plain", "text/html", "text/markdown", "text/xml", "text/csv", "text/yaml", "text/yml", "text/ini", "text/log"]):
                    continue

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
                        f"Первые 300 символов:\n```\n{preview}\n```"
                    )

                    await handle_violation(
                        self.bot,
                        message,
                        reason_title="Реклама внутри файла",
                        reason_text="реклама в прикреплённом файле",
                        extra_info=extra,
                        timeout_reason="Реклама в файле",
                        force_harsh=True
                    )

                    return
                
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        if guild.id != config.GUILD_ID:
            return

        if channel.id not in config.PROTECTED_CHANNELS_IDS:
            return

        # Ищем кто удалил канал
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

        # Если удалил бот -> ищем кто добавил бота (в течение 3 дней)
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

        # Никого не нашли -> подозрение на краш
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

        # Находим всех + баним каждого
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