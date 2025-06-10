import io
import typing
import discord

from aiocache import SimpleMemoryCache

from datetime import datetime, timezone

from discord     import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

from modules.configuration import config

snipe_cache = SimpleMemoryCache()

async def snippet(bot: LittleAngelBot, ci: discord.Interaction, channel: typing.Union[discord.StageChannel, discord.TextChannel, discord.VoiceChannel, discord.Thread], index: int, view: discord.ui.View = None, method: str = None):
    snipe_existing_data: typing.List = await snipe_cache.get(channel.id)
    rpos = len(snipe_existing_data)
    try:
        snipess = snipe_existing_data[int(index)]
    except:
        return await ci.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Произошло неожиданное изменение записей, вызовите команду, или нажмите кнопку ещё раз"), ephemeral=True)
    await ci.response.defer()
    s: discord.Message = snipess['msg']
    prava = snipess['perms']
    sniped_embed = discord.Embed(timestamp=s.created_at, color=config.LITTLE_ANGEL_COLOR, description=s.content)
    sniped_embed.set_author(name=s.author.display_name, icon_url=s.author.display_avatar.url, url=f"https://discord.com/users/{s.author.id}")
    if s.type == discord.MessageType.reply:
        try:
            sniped_embed.add_field(name="Ответил на:", value=f"[Это сообщение]({s.reference.resolved.jump_url})", inline=False)
        except:
            sniped_embed.add_field(name="Ответил на:", value=f"Удалённое сообщение", inline=False)
    if prava:
        deleted_user = snipess['deleted_user']
        if deleted_user:
            sniped_embed.add_field(name="Сообщение удалил:", value=f"{deleted_user} ({deleted_user.mention})", inline=False)
    else:
        sniped_embed.add_field(name="Внимание!", value="Бот не имеет доступа к журналу аудита для корректной работы команды!", inline=False)
    files = [discord.File(io.BytesIO(field['bytes']), filename=field['filename']) for field in snipess['files']]
    if s.stickers:
        sr = ""
        for sticker in s.stickers:
            sr += f"\n[{sticker.name}]({sticker.url}) (ID: {sticker.id})"
        sniped_embed.add_field(name="Стикеры:", value=sr, inline=False)
    if s.components:
        cr = ""
        for component in s.components:
            if isinstance(component, discord.Button):
                opis = f"{component.emoji or component.label}"
                if component.label and component.emoji:
                    opis += f"{component.label}"
                cr += f"\nКнопка ({opis})"
        sniped_embed.add_field(name="Компоненты:", value=cr, inline=False)
    sniped_embed.add_field(name="Позиция:", value=f"{index + 1} / {rpos}", inline=False)
    if not view:
        view = snipe_archive(bot, timeout=300, channel_id=channel.id, author_id=ci.user.id)
    else:
        view.timeout = 300
    embeds = [sniped_embed]
    if s.embeds and s.author.bot:
        if embeds[0].type == 'rich':
            embeds.insert(0, s.embeds[0])
    try:
        if method == "send":
            await ci.followup.send(embeds=embeds, files=files, view=view)
            view.message = await ci.original_response()
        elif method == "button_response":
            view.message = await ci.original_response()
            await ci.edit_original_response(embeds=embeds, attachments=files, view=view)
    except:
        if method == "send":
            await ci.followup.send(embeds=embeds, view=view, content="\n".join([a.proxy_url for a in s.attachments]))
            view.message = await ci.original_response()
        elif method == "button_response":
            view.message = await ci.original_response()
            await ci.edit_original_response(embeds=embeds, view=view, content="\n".join([a.proxy_url for a in s.attachments]))

class snipe_archive(discord.ui.View):
    def __init__(self, bot: LittleAngelBot = None, timeout: int = 300, message: discord.Message = None, author_id: int = None, channel_id: int = None):
        super().__init__()
        self.bot = bot
        self.message = message
        self.author_id = author_id
        self.channel_id = channel_id
        self.finished = False

    async def on_timeout(self) -> None:
        if self.finished:
            return
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="⬅")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        ipos = None
        epos = 0
        snipe_existing_data: typing.List = await snipe_cache.get(self.channel_id)
        if len(interaction.message.embeds) > 1:
            epos = 1
        for field in interaction.message.embeds[epos].fields:
            if field.name == "Позиция:":
                ipos = int(field.value.split()[0]) - 2
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Использовать интеграцию может только тот человек, который вызывал команду!", color=0xff0000), ephemeral=True)
        if ipos < 0:
            ipos = len(snipe_existing_data) - 1
        try:
            snipe_existing_data[ipos]
        except:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вызовите новую команду из-за того, что кто-то сбросил, или изменил архив"), ephemeral=True)
        channel = await self.bot.fetch_channel(self.channel_id)
        await snippet(self.bot, interaction, channel, ipos, self, "button_response")

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="➡")
    async def soon(self, interaction: discord.Interaction, button: discord.ui.Button):
        ipos = None
        epos = 0
        snipe_existing_data: typing.List = await snipe_cache.get(self.channel_id)
        if len(interaction.message.embeds) > 1:
            epos = 1
        for field in interaction.message.embeds[epos].fields:
            if field.name == "Позиция:":
                ipos = int(field.value.split()[0])
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Использовать интеграцию может только тот человек, который вызывал команду!", color=0xff0000), ephemeral=True)
        if ipos >= len(snipe_existing_data):
            ipos = 0
        try:
            snipe_existing_data[ipos]
        except:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вызовите новую команду из-за того, что кто-то сбросил, или изменил архив"), ephemeral=True)
        channel = await self.bot.fetch_channel(self.channel_id)
        await snippet(self.bot, interaction, channel, ipos, self, "button_response")

    @discord.ui.button(style=discord.ButtonStyle.red, emoji="🗑️")
    async def sdelete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(interaction.message.embeds) > 1:
            epos = 1
        else:
            epos = 0
        for field in interaction.message.embeds[epos].fields:
            if field.name == "Позиция:":
                position = int(field.value.split()[0]) - 1
        channel = await self.bot.fetch_channel(self.channel_id)
        if not channel.permissions_for(interaction.user).manage_messages:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права управлять сообщениями для использования этой кнопки!", color=0xff0000), ephemeral=True)
        try:
            snipe_existing_data: typing.List = await snipe_cache.get(self.channel_id)
            snipess: typing.Dict = snipe_existing_data[position]
            if int(interaction.message.embeds[epos].author.url.replace("https://discord.com/users/", "")) == snipess['msg'].author.id:
                snipe_existing_data.pop(position)
                await snipe_cache.set(self.channel_id, snipe_existing_data, ttl=3600)
            else:
                await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Данное сообщение уже было удалено из архива!", color=0xff0000), ephemeral=True)
                return await interaction.followup.delete_message(interaction.message.id)
        except:
            await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Данное сообщение уже было удалено из архива!", color=0xff0000), ephemeral=True)
            return await interaction.followup.delete_message(interaction.message.id)
        emb = discord.Embed(title="☑️ Успешно!", color=config.LITTLE_ANGEL_COLOR, description=f"Заархивированное сообщение с позицией {position + 1} было удалено!", timestamp=datetime.now(timezone.utc))
        emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar, url=f"https://discord.com/users/{interaction.user.id}")
        self.finished = True
        await interaction.response.edit_message(embed=emb, attachments=[], view=None)

    @discord.ui.button(style=discord.ButtonStyle.red, emoji="🧹")
    async def sreset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права управлять сообщениями для использования этой кнопки!", color=0xff0000), ephemeral=True)
        try:
            await snipe_cache.set(self.channel_id, [], ttl=3600)
        except:
            pass
        emb = discord.Embed(title="☑️ Успешно!", color=config.LITTLE_ANGEL_COLOR, description=f"Весь архив этого канала был стёрт!", timestamp=datetime.now(timezone.utc))
        emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar, url=f"https://discord.com/users/{interaction.user.id}")
        self.finished = True
        await interaction.response.edit_message(embed=emb, attachments=[], view=None)

class Snipe(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: typing.List[discord.Message]):
        now = int(datetime.now(timezone.utc).timestamp())

        channel_id = messages[0].channel.id
        existing = await snipe_cache.get(channel_id) or []

        deleted_user = False
        perms = False
        try:
            async for entry in messages[0].guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                perms = True
                if entry.target.id == channel_id and int(entry.created_at.timestamp()) == now:
                    deleted_user = entry.user
        except:
            pass

        for message in messages:
            if not message.is_system():
                try:
                    files = [{'bytes': await a.read(use_cached=True), 'filename': a.filename} for a in message.attachments]
                except:
                    files = [{'bytes': await a.read(use_cached=False), 'filename': a.filename} for a in message.attachments]
                existing.append({'msg': message, 'perms': perms, 'deleted_user': deleted_user, 'files': files})

        await snipe_cache.set(channel_id, existing, ttl=3600)


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.is_system() or message.author == self.bot.user:
            return
        if not message.guild:
            return

        now = int(datetime.now(timezone.utc).timestamp())

        channel_id = message.channel.id
        existing = await snipe_cache.get(channel_id) or []

        sdict = {
            'msg': message,
            'deleted_user': False,
            'perms': False
        }
        try:
            sdict['files'] = [{'bytes': await a.read(use_cached=True), 'filename': a.filename} for a in message.attachments]
        except:
            sdict['files'] = [{'bytes': await a.read(use_cached=False), 'filename': a.filename} for a in message.attachments]

        try:
            async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                sdict['perms'] = True
                if entry.target == message.author and entry.extra.channel.id == message.channel.id and int(entry.created_at.timestamp()) == now:
                    sdict['deleted_user'] = entry.user
        except:
            pass

        existing.append(sdict)
        await snipe_cache.set(channel_id, existing, ttl=3600)


    @app_commands.command(name="снайп", description="Показывает удалённые сообщения в канале")
    @app_commands.guild_only
    @app_commands.describe(channel='Выберите канал для отображения', position='Введите позицию')
    async def snipe(self, interaction: discord.Interaction, channel: typing.Union[discord.StageChannel, discord.TextChannel, discord.VoiceChannel, discord.Thread]=None, position: int=None):
        if not channel:
            channel = interaction.channel
        if channel.is_nsfw() and not interaction.channel.is_nsfw():
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Нельзя смотреть материалы с NSFW канала в канале без этой метки!"), ephemeral=True)
        
        snipe_existing_data: typing.List = await snipe_cache.get(channel.id)
        if not snipe_existing_data:
            raise KeyError()

        if not position:
            position = len(snipe_existing_data) - 1
        else:
            position = position - 1

        snipe_existing_data[position]

        await snippet(self.bot, interaction, channel, position, None, "send")

    @snipe.error
    async def snipe_error(self, interaction: discord.Interaction, error):
        if isinstance(getattr(error, "original", error), KeyError):
            await interaction.response.send_message(embed=discord.Embed(description="Нет удалённых сообщений в канале, либо вы ввели неверную позицию!", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)
        

async def setup(bot: LittleAngelBot):
    await bot.add_cog(Snipe(bot))
