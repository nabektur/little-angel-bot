import base64
import typing
import discord

from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

from modules.configuration import config

class TokenCommand(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="токен", description="Показывает начало токена у пользователя")
    @app_commands.describe(member='Выберите участника')
    async def token_command(self, interaction: discord.Interaction, member: typing.Union[discord.Member, discord.User] = None):
        if not member:
            member = interaction.user

        await interaction.response.send_message(content=member.mention, embed=discord.Embed(color=config.LITTLE_ANGEL_COLOR, description=f"Начало токена {member.mention}: `{base64.b64encode(str(member.id).encode('ascii')).decode('ascii').replace('=', '')}.`"))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(TokenCommand(bot))