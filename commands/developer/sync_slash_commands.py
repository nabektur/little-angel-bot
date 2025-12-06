import discord

from discord.ext           import commands

from classes.bot           import LittleAngelBot

from modules.configuration import config

class SyncSlashCommands(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guild_id: int=None):
        if guild_id:
            await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        else:
            await self.bot.tree.sync(guild=None)
        await ctx.send(embed=discord.Embed(description="☑️ Синхронизировано!", color=config.LITTLE_ANGEL_COLOR))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(SyncSlashCommands(bot))