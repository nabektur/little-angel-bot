import typing
import discord
import asyncio

from datetime                  import timedelta, datetime, timezone
from apscheduler.triggers.date import DateTrigger

from discord import app_commands
from discord.ext import commands

from classes.bot       import LittleAngelBot
from classes.database  import db

from modules.configuration  import config

async def is_autopub(channel_id: int):
    return await db.fetchone("SELECT channel_id FROM autopublish WHERE channel_id = $1", channel_id) != None


class AutoPublish(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    autopublish_group = app_commands.Group(
        name="автопубликация",
        description="Автоматическая публикация новостей",
        guild_only=True,
        default_permissions=discord.Permissions(manage_channels=True)
    )

    @autopublish_group.command(name="включить", description="Включает автопубликацию новостей на сервере")
    @app_commands.describe(channel="Выберите новостной канал для автоматической публикации")
    async def autopub_turn_on_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not channel.is_news():
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Функция автопубликации недоступна в НЕ новостных каналах!"), ephemeral=True)
        channel_permissions = channel.permissions_for(interaction.guild.me)
        if not (channel_permissions.read_messages and channel_permissions.send_messages and channel_permissions.manage_messages and channel_permissions.read_message_history):
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Бот не может публиковать сообщения в указанном канале! Убедитесь, что в новостном канале бот может просматривать сам канал, отправлять сообщения, управлять ими и читать историю сообщений"), ephemeral=True)
        await db.execute("INSERT INTO autopublish (channel_id) VALUES($1);", channel.id)
        await interaction.response.send_message(embed=discord.Embed(color=config.LITTLE_ANGEL_COLOR, title="✅ Успешно!", description=f"Автопубликация включена!"))
        
    @autopublish_group.command(name="выключить", description="Выключает автопубликацию новостей на сервере")
    @app_commands.describe(channel="Выберите новостной канал автоматической публикации")
    async def autopub_turn_off_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not channel.is_news():
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="Функция автопубликации недоступна в НЕ новостных каналах!"), ephemeral=True)
        if await is_autopub(channel.id):
            await db.execute("DELETE FROM autopublish WHERE channel_id = $1;", channel.id)
            return await interaction.response.send_message(embed=discord.Embed(color=config.LITTLE_ANGEL_COLOR, title="☑️ Успешно!", description="Автопубликация была выключена!"))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="❌ Ошибка!", color=0xff0000, description="В этом канале не была включена автопубликация!"), ephemeral=True)

async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoPublish(bot))
