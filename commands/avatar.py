import discord

from discord import app_commands, Embed
from discord.ext import commands

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Показать аватар")
    async def avatar(self, interaction):
        user = interaction.user
        embed = Embed(
            title=f"Аватар {user.name}!",
            color=discord.Color.random()
        )
        embed.set_image(url=user.display_avatar.url)
        embed.set_footer(text=f"Запрошено {user.name}")
        embed.timestamp = interaction.created_at
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
