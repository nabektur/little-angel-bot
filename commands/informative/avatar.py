import typing
import discord

from discord     import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

class Avatar(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="аватар", description="Показывает аватар участника")
    @app_commands.describe(member='Выберите участника')
    async def avatar(self, interaction: discord.Interaction, member: typing.Union[discord.Member, discord.User]=None):
        await interaction.response.defer()
        if not member:
            member = interaction.user

        embeds = []
        avatars = []

        user = await self.bot.fetch_user(member.id)
        user_avatar = await user.display_avatar.to_file()

        try:
            guild_member = await interaction.guild.fetch_member(member.id)
        except:
            guild_member = None

        embeds.append(discord.Embed(title=f"Аватар {user}", color=(guild_member or user).accent_color or member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{user_avatar.filename}"))
        avatars.append(user_avatar)

        if guild_member:
            if guild_member.guild_avatar:
                guild_avatar = await guild_member.display_avatar.to_file()
                embeds.append(discord.Embed(title=f"Аватар {user} на сервере", color=(guild_member or user).accent_color or member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{guild_avatar.filename}"))
                avatars.append(guild_avatar)
        
        await interaction.followup.send(embeds=embeds, files=avatars)

async def setup(bot: LittleAngelBot):
    await bot.add_cog(Avatar(bot))
