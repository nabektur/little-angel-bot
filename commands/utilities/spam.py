import typing
import discord
import asyncio

from datetime import timedelta, datetime, timezone

from discord import app_commands
from discord.ext import commands

from classes.bot      import LittleAngelBot
from classes.database import db

from modules.time_converter import Duration, verbose_timedelta
from modules.spam_runner    import run_spam
from modules.configuration  import config

class Spam(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot
        
    async def spam_activate(self, interaction: discord.Interaction, type: str, method: str, channel: discord.abc.GuildChannel, duration: typing.Optional[datetime], mention: str):
        channel_permissions = channel.permissions_for(interaction.guild.me)
        if method == "webhook":
            try:
                if isinstance(channel, discord.Thread):
                    wchannel = channel.parent
                else:
                    wchannel = channel
                webhooks = await wchannel.webhooks()
                webhook = [webhook for webhook in webhooks if(webhook.name == "Ангелочек")]
                if webhook:
                    webhook = webhook[0]
                else:
                    webhook = await wchannel.create_webhook(name="Ангелочек", avatar=await self.bot.user.avatar.read())
            except:
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права управлять вебхуками для использования этой команды!"), ephemeral=True)
        else:
            if channel.slowmode_delay and not channel_permissions.manage_messages:
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права управлять сообщениями! Это право нужно боту для того чтобы избегать медленного режима"), ephemeral=True)
            webhook = None
        if isinstance(channel, discord.Thread):
            if not channel_permissions.send_messages_in_threads:
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права высылать сообщения в эту ветку для использования этой команды!"), ephemeral=True)
        else:
            if not channel_permissions.send_messages:
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права высылать сообщения в этот канал для использования этой команды!"), ephemeral=True)
        if await db.fetchone("SELECT channel_id FROM spams WHERE channel_id = $1 LIMIT 1", channel.id):
            await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", description="Спам уже включён в данном канале!", color=0xff0000), ephemeral=True)
        else:
            await interaction.response.defer()
            if duration:
                duration_timedelta = duration
                duration = datetime.now(timezone.utc) + duration
                await interaction.followup.send(embed=discord.Embed(description=f'☑️ Спам активирован на {verbose_timedelta(duration_timedelta)} (<t:{int(duration.timestamp())}:R>)!', color=config.LITTLE_ANGEL_COLOR))
            else:
                await interaction.followup.send(embed=discord.Embed(description='☑️ Спам активирован!', color=config.LITTLE_ANGEL_COLOR))
            if channel != interaction.channel:
                if duration:
                    await channel.send(embed=discord.Embed(description=f'☑️ Спам активирован по команде {interaction.user.mention} на {verbose_timedelta(duration_timedelta)} (<t:{int(duration.timestamp())}:R>)!', color=config.LITTLE_ANGEL_COLOR))
                else:
                    await channel.send(embed=discord.Embed(description=f'☑️ Спам активирован по команде {interaction.user.mention}!', color=config.LITTLE_ANGEL_COLOR))
            await db.execute("INSERT INTO spams (type, method, channel_id, ments, timestamp) VALUES($1, $2, $3, $4, $5) ON CONFLICT (channel_id) DO UPDATE SET type = EXCLUDED.type, method = EXCLUDED.method, ments = EXCLUDED.ments, timestamp = EXCLUDED.timestamp;", type, method, channel.id, mention, f"{int(duration.timestamp())}" if duration else None)
            asyncio.create_task(run_spam(type, method, channel, webhook, mention, duration))

    spam_group = app_commands.Group(
        name="спам",
        description="Спам в канале",
        guild_only=True,
        default_permissions=discord.Permissions(mention_everyone=True, moderate_members=True)
    )
        
    @spam_group.command(name="остановить", description="Останавливает спам в канале")
    @app_commands.describe(channel='Выберите канал для спама')
    async def spam_stop_command(self, interaction: discord.Interaction, channel: typing.Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]=None):
        if not channel:
            channel = interaction.channel
        if await db.fetchone("SELECT channel_id FROM spams WHERE channel_id = $1 LIMIT 1", channel.id):
            await interaction.response.defer()
            await db.execute("DELETE FROM spams WHERE channel_id = $1;", channel.id)
            await interaction.followup.send(embed=discord.Embed(description='☑️ Спам остановлен!', color=config.LITTLE_ANGEL_COLOR))
            if not channel == interaction.channel:
                await channel.send(embed=discord.Embed(description=f'☑️ Спам остановлен по команде {interaction.user.mention}!', color=config.LITTLE_ANGEL_COLOR))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", description="Спам не включён в данном канале!", color=0xff0000), ephemeral=True)
        

    class CustomSpamModal(discord.ui.Modal, title='Кастомный текст'):
        def __init__(self, parent: 'Spam', method, channel, duration, mention):
            super().__init__()
            self.parent = parent
            self.method = method
            self.channel = channel
            self.duration = duration
            self.mention = mention

        appeal = discord.ui.TextInput(
            label='Текст:',
            placeholder='Введите сюда текст. Если вы хотите несколько текстов, то разделите их символом |',
            required=True,
            style=discord.TextStyle.long
        )

        async def on_submit(self, interaction: discord.Interaction):
            await self.parent.spam_activate(
                interaction=interaction,
                type=self.appeal.value,
                method=self.method,
                channel=self.channel,
                duration=self.duration,
                mention=self.mention
            )

    @spam_group.command(name="активировать", description="Начинает спам в канале")
    @app_commands.choices(type=[app_commands.Choice(name="Спам текстом по умолчанию", value="default"), app_commands.Choice(name="Спам кастомным текстом", value="custom")], method=[app_commands.Choice(name="Спам через бота", value="bot"), app_commands.Choice(name="Спам через вебхук", value="webhook")])
    @app_commands.describe(type="Выберите тип спама", method="Выберите метод спама", channel='Выберите канал для спама', duration='Укажите длительность спама', mention_1='Упомяните роль/участника, которые будут пинговаться', mention_2='Упомяните роль/участника, которые будут пинговаться', mention_3='Упомяните роль/участника, которые будут пинговаться', mention_4='Упомяните роль/участника, которые будут пинговаться', mention_5='Упомяните роль/участника, которые будут пинговаться')
    async def spam_activate_command(self, interaction: discord.Interaction, type: str, method: str, channel: typing.Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]=None, duration: app_commands.Transform[str, Duration]="", mention_1: typing.Union[discord.Role, discord.User]=None, mention_2: typing.Union[discord.Role, discord.User]=None, mention_3: typing.Union[discord.Role, discord.User]=None, mention_4: typing.Union[discord.Role, discord.User]=None, mention_5: typing.Union[discord.Role, discord.User]=None):
        if not channel:
            channel = interaction.channel
        if duration:
            if duration > timedelta(days=365) or duration < timedelta(seconds=3):
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы указали длительность, которая больше, чем 1 год, либо меньше, чем 3 секунды!"), ephemeral=True)
        if not isinstance(channel, typing.Union[discord.TextChannel, discord.Thread, discord.VoiceChannel]):
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Команду можно применять только к текстовым каналам, веткам и голосовым каналам!"), ephemeral=True)
        mention = []
        if mention_1:
            mention.append(mention_1)
        if mention_2:
            mention.append(mention_2)
        if mention_3:
            mention.append(mention_3)
        if mention_4:
            mention.append(mention_4)
        if mention_5:
            mention.append(mention_5)
        mention = [u.mention if u != interaction.guild.default_role else "@everyone" for u in mention]
        if mention:
            if not interaction.guild.me.guild_permissions.mention_everyone:
                return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права упоминать @everyone и @here для использования этой команды с включёнными упоминаниями!"), ephemeral=True)
            if self.bot.user.mention in mention:
                mention.remove(self.bot.user.mention)
            mention = " ".join(list(set(mention)))
        else:
            mention = ""
        if type == "custom":
            modal = self.CustomSpamModal(
                parent=self,
                method=method,
                channel=channel,
                duration=duration,
                mention=mention
            )
            return await interaction.response.send_modal(modal)
        await self.spam_activate(interaction=interaction, type=type, method=method, channel=channel, duration=duration, mention=mention)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(Spam(bot))
