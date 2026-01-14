import discord
from discord.ext import commands

from classes.bot import LittleAngelBot
from classes.database import db
from modules.configuration import config

class UnblockUser(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.command(name="unblock", description="Разблокировать пользователя")
    @commands.is_owner()
    async def unblock_user_command(self, ctx: commands.Context, *, user_id: int):
        await db.execute("DELETE FROM blocked_users WHERE user_id = ?;", user_id)
        await ctx.reply(embed=discord.Embed(description="☑️ Пользователь разблокирован!", color=config.LITTLE_ANGEL_COLOR))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(UnblockUser(bot))