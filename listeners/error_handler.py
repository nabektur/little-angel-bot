import discord

from discord.ext          import commands
from discord.ext.commands import CommandNotFound

from classes.bot import LittleAngelBot

from modules.configuration  import config


class ErrorHandler(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    
    @commands.Cog.listener()
    async def on_command_error(ctx, error):
        if isinstance(error, CommandNotFound):
            return
        raise error


async def setup(bot: LittleAngelBot):
    await bot.add_cog(ErrorHandler(bot))
