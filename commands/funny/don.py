import random
import discord

from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

class Don(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot
    
    @app_commands.command(name='дон', description='Бот связывается с Рамзаном Кадыровым')
    @app_commands.guild_only
    async def don(interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(['Чечня гордица вами дон!\nРазман катырав предаставмц вам 2 авца жына дон!\nПрадалжайте радовать чечня!', 'Чечня не гордица вами дон!\nРазман катырав атаброл у вос 2 авца жына дон!\nhttps://tenor.com/view/%D0%B8%D0%B7%D0%B2%D0%B8%D0%BD%D0%B8%D1%81%D1%8C-%D0%BA%D0%B0%D0%B4%D1%8B%D1%80%D0%BE%D0%B2-%D1%80%D0%B0%D0%BC%D0%B7%D0%B0%D0%BD-%D1%80%D0%B0%D0%BC%D0%B7%D0%B0%D0%BD%D0%BA%D0%B0%D0%B4%D1%8B%D1%80%D0%BE%D0%B2-%D0%B8%D0%B7%D0%B2%D0%B8%D0%BD%D0%B8%D1%81%D1%8C%D1%81%D0%B5%D0%B9%D1%87%D0%B0%D1%81%D0%B6%D0%B5-gif-22796883']))


async def setup(bot: LittleAngelBot):
    await bot.add_cog(Don(bot))