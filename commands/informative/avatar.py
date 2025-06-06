import typing
import discord

from discord import app_commands
from discord.ext import commands

from modules.bot_class import LittleAngelBot

class Avatar(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Показывает аватар участника")
    @app_commands.describe(member='Выберите участника')
    async def avatar(self, interaction: discord.Interaction, member: typing.Union[discord.Member, discord.User]=None):
        await interaction.response.defer()
        if not member:
            member = interaction.user

        embeds = []
        avatars = []

        user = await self.bot.fetch_user(member.id)
        user_avatar = await user.display_avatar.to_file()

        embeds.append(discord.Embed(title=f"Аватар {user}", color=member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{user_avatar.filename}"))
        avatars.append(user_avatar)

        if isinstance(member, discord.Member):
            if member.guild_avatar:
                guild_avatar = await member.display_avatar.to_file()
                embeds.append(discord.Embed(title=f"Аватар {user} на сервере", color=member.color, url=f"https://discord.com/users/{member.id}").set_image(url=f"attachment://{guild_avatar.filename}"))
                avatars.append(guild_avatar)
        
        await interaction.followup.send(embeds=embeds, files=avatars)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
