import typing
import discord

from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

class AutoRemoveMessages(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    # @app_commands.command(name="автоудаление", description="Автоматически удаляет сообщение через время")
    # @app_commands.guild_only()
    # @app_commands.default_permissions(manage_messages=True)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(AutoRemoveMessages(bot))
