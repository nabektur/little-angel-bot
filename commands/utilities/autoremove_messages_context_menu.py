import typing
import discord
import asyncio

from datetime                  import timedelta, datetime, timezone
from apscheduler.triggers.date import DateTrigger

from discord import app_commands
from discord.ext import commands

from classes.bot       import LittleAngelBot
from classes.database  import db
from classes.scheduler import scheduler

from modules.time_converter import Duration, verbose_timedelta
from modules.configuration  import config

async def delayed_delete_message(message_id: int, channel_id: int):
    from classes.bot import bot

    channel = bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    await message.delete()

class DurationModal(discord.ui.Modal, title="Удаление сообщения позже"):
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message

        self.add_item(discord.ui.TextInput(
            label="Через через? (например: 10c, 5мин, 2ч, 1д)",
            placeholder="1 ч 30 мин",
            custom_id="duration_input"
        ))

    async def on_submit(self, interaction: discord.Interaction):

        try:
            duration = await Duration().transform(interaction, self.children[0].value)
        except:
            return

        if duration > timedelta(days=30) or duration < timedelta(seconds=3):
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы указали длительность, которая больше, чем 1 месяц, либо меньше, чем 3 секунды!"), ephemeral=True)

        duration_datetime = datetime.now(timezone.utc) + duration
        scheduler.add_job(delayed_delete_message, trigger=DateTrigger(run_date=duration), args=[self.message.id, self.message.channel.id])

        await interaction.response.send_message(embed=discord.Embed(title="☑️ Принято!", color=config.LITTLE_ANGEL_COLOR, description=f"Бот удалит указанное сообщение через {verbose_timedelta(duration)} (<t:{int(duration_datetime.timestamp())}:R>)"), ephemeral=True)

@app_commands.context_menu(name="Удалить сообщение позже")
async def delayed_delete_context(interaction: discord.Interaction, message: discord.Message):
    member_perms = message.channel.permissions_for(interaction.user)
    if message.author.id != interaction.user.id and not member_perms.manage_messages:
        return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Вы не можете удалять чужие сообщения без права на управление сообщениями!"), ephemeral=True)
    
    await interaction.response.send_modal(DurationModal(message))

async def setup(bot: LittleAngelBot):
    bot.tree.add_command(delayed_delete_context)