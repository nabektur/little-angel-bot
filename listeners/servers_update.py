import discord
from discord.ext import commands

from classes.bot import LittleAngelBot
from modules.configuration import CONFIG

class ServersUpdate(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id != CONFIG.GUILD_ID:
            await guild.leave()
            return
        
        success = False
        for channel in guild.text_channels:
            try:
                await channel.send(embed=discord.Embed(color=CONFIG.LITTLE_ANGEL_COLOR, title="Привет!", description=f"Спасибо, что добавили меня на ваш сервер!\n\nКоманды можете посмотреть, введя </хелп:1381175398473273354>\n\n🍀 Удачи!"))
                success = True
            except discord.Forbidden:
                pass
            if success:
                break

        log_channel = self.bot.get_channel(CONFIG.BOT_LOGS_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="Бот был добавлен на сервер", color=CONFIG.LITTLE_ANGEL_COLOR, description = f"Участников: {guild.member_count}\nID сервера: {guild.id}")
            user = None
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                    user = entry.user
            except discord.Forbidden:
                ...
            if user:
                embed.description = f"Добавил: {user.mention} ({user}) с ID: {user.id}\n" + embed.description
            embed.set_footer(icon_url=guild.icon.url if guild.icon else None, text=guild.name)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        log_channel = self.bot.get_channel(CONFIG.BOT_LOGS_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="Бот был удалён с сервера", description=f"Участников: {guild.member_count}\nID сервера: {guild.id}", color=CONFIG.LITTLE_ANGEL_COLOR)
            embed.set_footer(icon_url=guild.icon.url if guild.icon else None, text=guild.name)
            await log_channel.send(embed=embed)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(ServersUpdate(bot))
