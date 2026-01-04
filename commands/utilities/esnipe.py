import typing
import logging
import discord
import traceback

from aiocache              import SimpleMemoryCache

from datetime              import datetime, timezone

from discord               import app_commands
from discord.ext           import commands

from classes.bot           import LittleAngelBot

from modules.configuration import config

esnipe_cache = SimpleMemoryCache()

class esnipe_archive(discord.ui.View):
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
    async def eback(self, interaction: discord.Interaction, button: discord.ui.Button):
        ipos = None
        for field in interaction.message.embeds[0].fields:
            if field.name == "Позиция:":
                ipos = int(field.value.split()[0]) - 2
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Использовать интеграцию может только тот человек, который вызывал команду!", color=0xff0000), ephemeral=True)
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                logging.error(f"ESnipe: Не удалось получить канал по ID {self.channel_id}: {e}\n{traceback.format_exc()}")
                return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Не удалось получить канал для проверки прав доступа!", color=0xff0000), ephemeral=True)
        user_permissions_in_channel = channel.permissions_for(interaction.user)
        if user_permissions_in_channel.read_message_history == False or user_permissions_in_channel.read_messages == False:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права просматривать этот канал или читать историю сообщений в нём!", color=0xff0000), ephemeral=True)

        esnipe_existing_data: typing.List = await esnipe_cache.get(self.channel_id)
        if ipos < 0:
            ipos = len(esnipe_existing_data) - 1
        try:
            rpos = len(esnipe_existing_data)
            esnipe_existing_data[ipos]
        except:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вызовите новую команду из-за того, что кто-то сбросил, или изменил архив"), ephemeral=True)
        await interaction.response.defer()

        self.timeout = 300
        es = esnipe_existing_data[ipos]
        before: discord.Message = es['before']
        after: discord.Message = es['after']
        if not before.content:
            before.content = "**Нет содержания**"
        if not after.content:
            after.content = "**Нет содержания**"
        await interaction.edit_original_response(view=self, embed=discord.Embed(description=f"**До изменения:**\n{before.content}\n**После:**\n{after.content}", color=config.LITTLE_ANGEL_COLOR).set_author(name=before.author.display_name, icon_url=before.author.display_avatar.url, url=f"https://discord.com/users/{before.author.id}").add_field(name="Позиция:", value=f"{ipos + 1} / {rpos}", inline=False).add_field(name="Ссылка на сообщение", value=f"[Перейти]({after.jump_url})", inline=False))

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="➡")
    async def esoon(self, interaction: discord.Interaction, button: discord.ui.Button):
        ipos = None
        for field in interaction.message.embeds[0].fields:
            if field.name == "Позиция:":
                ipos = int(field.value.split()[0])
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Использовать интеграцию может только тот человек, который вызывал команду!", color=0xff0000), ephemeral=True)
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                logging.error(f"ESnipe: Не удалось получить канал по ID {self.channel_id}: {e}\n{traceback.format_exc()}")
                return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="Не удалось получить канал для проверки прав доступа!", color=0xff0000), ephemeral=True)
        user_permissions_in_channel = channel.permissions_for(interaction.user)
        if user_permissions_in_channel.read_message_history == False or user_permissions_in_channel.read_messages == False:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права просматривать этот канал или читать историю сообщений в нём!", color=0xff0000), ephemeral=True)

        esnipe_existing_data: typing.List = await esnipe_cache.get(self.channel_id)

        if ipos >= len(esnipe_existing_data):
            ipos = 0
        try:
            rpos = len(esnipe_existing_data)
            esnipe_existing_data[ipos]
        except:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вызовите новую команду из-за того, что кто-то сбросил, или изменил архив"), ephemeral=True)
        await interaction.response.defer()

        self.timeout = 300
        es = esnipe_existing_data[ipos]
        before: discord.Message = es['before']
        after: discord.Message = es['after']
        if not before.content:
            before.content = "**Нет содержания**"
        if not after.content:
            after.content = "**Нет содержания**"
        await interaction.edit_original_response(view=self, embed=discord.Embed(description=f"**До изменения:**\n{before.content}\n**После:**\n{after.content}", color=config.LITTLE_ANGEL_COLOR).set_author(name=before.author.display_name, icon_url=before.author.display_avatar.url, url=f"https://discord.com/users/{before.author.id}").add_field(name="Позиция:", value=f"{ipos + 1} / {rpos}", inline=False).add_field(name="Ссылка на сообщение", value=f"[Перейти]({after.jump_url})", inline=False))

    @discord.ui.button(style=discord.ButtonStyle.red, emoji="🗑️")
    async def edelete(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            esnipe_existing_data: typing.List = await esnipe_cache.get(self.channel_id)
            snipess: typing.Dict = esnipe_existing_data[position]
            if int(interaction.message.embeds[epos].author.url.replace("https://discord.com/users/", "")) == snipess['before'].author.id:
                esnipe_existing_data.pop(position)
                await esnipe_cache.set(self.channel_id, esnipe_existing_data, ttl=3600)
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
    async def ereset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права управлять сообщениями для использования этой кнопки!", color=0xff0000), ephemeral=True)
        try:
            await esnipe_cache.set(self.channel_id, [], ttl=3600)
        except:
            pass
        emb = discord.Embed(title="☑️ Успешно!", color=config.LITTLE_ANGEL_COLOR, description=f"Весь архив этого канала был стёрт!", timestamp=datetime.now(timezone.utc))
        emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar, url=f"https://discord.com/users/{interaction.user.id}")
        self.finished = True
        await interaction.response.edit_message(embed=emb, attachments=[], view=None)

class ESnipe(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message):
        guild = message_after.guild
        if not guild:
            return
        if message_after.author.bot:
            return
        if message_before.content == message_after.content:
            return

        channel_id = message_after.channel.id
        existing = await esnipe_cache.get(channel_id) or []
        existing.append({'before': message_before, 'after': message_after})
        await esnipe_cache.set(channel_id, existing, ttl=3600)


    @app_commands.command(name="еснайп", description = "Показывает изменённые сообщения")
    @app_commands.guild_only
    @app_commands.describe(channel='Выберите канал для отображения', position='Введите позицию')
    async def esnipe(self, interaction: discord.Interaction, channel: typing.Union[discord.StageChannel, discord.TextChannel, discord.VoiceChannel, discord.Thread]=None, position: int=None):
        if not channel:
            channel = interaction.channel
        if channel.is_nsfw() and not interaction.channel.is_nsfw():
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Нельзя смотреть материалы с NSFW канала в канале без этой метки!"), ephemeral=True)
        
        user_permissions_in_channel = channel.permissions_for(interaction.user)
        if user_permissions_in_channel.read_message_history == False or user_permissions_in_channel.read_messages == False:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="У вас нет права просматривать этот канал или читать историю сообщений в нём!", color=0xff0000), ephemeral=True)

        esnipe_existing_data: typing.List = await esnipe_cache.get(channel.id)
        if not esnipe_existing_data:
            raise KeyError()
        
        rpos = len(esnipe_existing_data)
        if not position:
            position = rpos - 1
        else:
            position = position - 1
        es = esnipe_existing_data[position]
        before: discord.Message = es['before']
        after: discord.Message = es['after']
        if not before.content:
            before.content = "**Нет содержания**"
        if not after.content:
            after.content = "**Нет содержания**"
        view = esnipe_archive(self.bot, timeout=300, channel_id=channel.id, author_id=interaction.user.id)
        await interaction.response.send_message(view=view, embed=discord.Embed(description=f"**До изменения:**\n{before.content}\n**После:**\n{after.content}", color=config.LITTLE_ANGEL_COLOR).set_author(name=before.author.display_name, icon_url=before.author.display_avatar.url, url=f"https://discord.com/users/{before.author.id}").add_field(name="Позиция:", value=f"{position + 1} / {rpos}", inline=False).add_field(name="Ссылка на сообщение", value=f"[Перейти]({after.jump_url})", inline=False))
        view.message = await interaction.original_response()

    @esnipe.error
    async def esnipe_error(self, interaction: discord.Interaction, error):
        if isinstance(getattr(error, "original", error), KeyError):
            await interaction.response.send_message(embed=discord.Embed(description="Нет изменённых сообщений в канале, либо вы ввели неверную позицию!", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(ESnipe(bot))
