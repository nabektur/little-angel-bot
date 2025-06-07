import typing
import discord

from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

from modules.configuration import config

class Boost(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name='бусты', description='Показывает информацию про бусты')
    @app_commands.guild_only
    async def boosts_info_command(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild.premium_subscription_count == 0:
            return await interaction.response.send_message(embed=discord.Embed(title="Ошибка! ❌", description="На сервере нет бустов!", color=0xff0000), ephemeral=True)
        boosters = guild.premium_subscribers
        boosters_str = ""
        for booster in boosters:
            boosters_str += f"\n{booster} ({booster.mention}) — Бустит с <t:{int(booster.premium_since.timestamp())}>"
        if boosters:
            return await interaction.response.send_message(embed=discord.Embed(title="Информация про бусты", color=0xf569fa, description=f"Уровень сервера: {guild.premium_tier}\nКоличество бустеров: {len(boosters)}\nКоличество бустов: {guild.premium_subscription_count}\nРоль для бустеров: {guild.premium_subscriber_role.mention}\nБустеры:{boosters_str}"))
        else:
            return await interaction.response.send_message(embed=discord.Embed(title="Информация про бусты", color=0xf569fa, description=f"Уровень сервера: {guild.premium_tier}\nКоличество бустеров: {len(boosters)}\nКоличество бустов: {guild.premium_subscription_count}\nРоль для бустеров: {guild.premium_subscriber_role.mention}"))


async def setup(bot: LittleAngelBot):
    await bot.add_cog(Boost(bot))
