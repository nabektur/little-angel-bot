import typing

import discord
from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot
from modules.configuration import config

class Banner(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="баннер", description="Показывает баннер участника")
    @app_commands.describe(member='Выберите участника')
    async def banner(self, interaction: discord.Interaction, member: typing.Union[discord.Member, discord.User]=None):
        await interaction.response.defer()
        if not member:
            member = interaction.user

        embeds = []
        banners = []

        try:
            guild_member = await interaction.guild.fetch_member(member.id)
        except:
            guild_member = None

        user = await self.bot.fetch_user(member.id)
        if user.banner:
            user_banner = await user.banner.to_file()
            embeds.append(discord.Embed(title=f"Баннер {user}", color=(guild_member or user).accent_color or member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{user_banner.filename}"))
            banners.append(user_banner)

        if guild_member:
            if guild_member.guild_banner:
                guild_banner = await guild_member.guild_banner.to_file()
                embeds.append(discord.Embed(title=f"Баннер {user} на сервере", color=(guild_member or user).accent_color or member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{guild_banner.filename}"))
                banners.append(guild_banner)

        if banners:
            await interaction.followup.send(embeds=embeds, files=banners)
        else:
            await interaction.followup.send(embed=discord.Embed(description="У данного участника нет баннера", color=config.LITTLE_ANGEL_COLOR))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(Banner(bot))
