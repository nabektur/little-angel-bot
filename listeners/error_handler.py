from discord.ext import commands

from classes.bot import LittleAngelBot


class ErrorHandler(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error


async def setup(bot: LittleAngelBot):
    await bot.add_cog(ErrorHandler(bot))
