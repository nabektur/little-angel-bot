from apscheduler.triggers.date import DateTrigger
from datetime import timedelta, datetime, timezone
import discord
from discord import app_commands

from classes.bot import LittleAngelBot
from classes.database import db
from classes.scheduler import scheduler
from modules.configuration import config
from modules.time_converter import Duration, verbose_timedelta

async def delayed_delete_message(message_id: int, channel_id: int):
    from classes.bot import bot

    channel = bot.get_channel(channel_id)
    await channel.delete_messages(
        [
            discord.Object(id=message_id)
        ]
    )

class DurationModal(discord.ui.Modal, title="Удаление сообщения позже"):
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message

        self.add_item(discord.ui.TextInput(
            label="Удалить через? (например: 10c, 5мин, 2ч, 1д)",
            placeholder="1 ч 30 мин"
        ))

    async def on_submit(self, interaction: discord.Interaction):

        try:
            duration = await Duration().transform(interaction, self.children[0].value)
        except:
            return
        
        if self.message.author.id != interaction.user.id and not self.message.channel.permissions_for(interaction.user).manage_messages:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы не можете удалять чужие сообщения без права на управление сообщениями!"), ephemeral=True)

        if duration > timedelta(days=30) or duration < timedelta(seconds=3):
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы указали длительность, которая больше, чем 1 месяц, либо меньше, чем 3 секунды!"), ephemeral=True)

        channel_permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not (channel_permissions.read_messages and channel_permissions.read_message_history):
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права просматривать указанный канал или просматривать историю его сообщений для использования этой команды!"), ephemeral=True)
        if not channel_permissions.manage_messages:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права управлять сообщениями в канале для использования этой команды!"), ephemeral=True)

        duration_datetime: datetime = datetime.now(timezone.utc) + duration

        await interaction.response.send_message(embed=discord.Embed(title="☑️ Принято!", color=config.LITTLE_ANGEL_COLOR, description=f"Бот удалит указанное сообщение через {verbose_timedelta(duration)} (<t:{int(duration_datetime.timestamp())}:R>)\n\n**[Ссылка на сообщение]({self.message.jump_url})**"), ephemeral=True)

        scheduler.add_job(delayed_delete_message, trigger=DateTrigger(run_date=duration_datetime), args=[self.message.id, self.message.channel.id])

@app_commands.context_menu(name="Удалить сообщение позже")
async def delayed_delete_context(interaction: discord.Interaction, message: discord.Message):
    if message.author.id != interaction.user.id and not message.channel.permissions_for(interaction.user).manage_messages:
        return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы не можете удалять чужие сообщения без права на управление сообщениями!"), ephemeral=True)
    
    channel_permissions = interaction.channel.permissions_for(interaction.guild.me)
    if not (channel_permissions.read_messages and channel_permissions.read_message_history):
        return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права просматривать указанный канал или просматривать историю его сообщений для использования этой команды!"), ephemeral=True)
    if not channel_permissions.manage_messages:
        return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="У бота нет права управлять сообщениями в канале для использования этой команды!"), ephemeral=True)

    await interaction.response.send_modal(DurationModal(message))

async def setup(bot: LittleAngelBot):
    bot.tree.add_command(delayed_delete_context)