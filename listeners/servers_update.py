import discord

from discord.ext import commands

from classes.bot import LittleAngelBot

from modules.configuration  import config


class ServersUpdate(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        success = False
        for channel in guild.text_channels:
            try:
                await channel.send(embed=discord.Embed(color=config.LITTLE_ANGEL_COLOR, title="Привет! 👋", description=f"Спасибо, что добавили меня на ваш сервер! 🙏")) # Подробнее о командах — </хелп:0>
                success = True
            finally:
                if success:
                    break

        log_channel = self.bot.get_channel(int(config.BOT_LOGS_CHANNEL_ID.get_secret_value()))
        if log_channel:
            embed = discord.Embed(title="Бот был добавлен на сервер", color=config.LITTLE_ANGEL_COLOR, description = f"Участников: {guild.member_count}\nID сервера: {guild.id}")
            user = None
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                    user = entry.user
            except:
                pass
            if user:
                embed.description = f"Добавил: {user.mention} ({user}) с ID: {user.id}\n" + embed.description
            if guild.icon:
                embed.set_footer(icon_url=guild.icon.url, text=guild.name)
            else:
                embed.set_footer(text=guild.name)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        log_channel = self.bot.get_channel(int(config.BOT_LOGS_CHANNEL_ID.get_secret_value()))
        if log_channel:
            embed = discord.Embed(title="Бот был кикнут/забанен с сервера", description=f"Участников: {guild.member_count}\nID сервера: {guild.id}", color=config.LITTLE_ANGEL_COLOR)
            if guild.icon:
                embed.set_footer(icon_url=guild.icon.url, text=guild.name)
            else:
                embed.set_footer(text=guild.name)
            await log_channel.send(embed=embed)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(ServersUpdate(bot))
