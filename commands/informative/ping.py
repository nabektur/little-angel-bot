import time
import logging
import traceback
import discord

from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot

from classes.database import db

_log = logging.getLogger(__name__)

class Ping(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="пинг", description="Показывает задержку бота")
    async def ping(self, interaction: discord.Interaction):
        start_rest_latency = time.monotonic()
        await interaction.response.send_message("🏓 Считаю пинг...")
        end_rest_latency = time.monotonic()

        start_database_latency = time.monotonic()
        await db.fetchone("SELECT * FROM spamtexts_ordinary LIMIT 1;")
        end_database_latency = time.monotonic()

        ws_latency = round(self.bot.latency * 1000)
        rest_latency = round((end_rest_latency - start_rest_latency) * 1000)
        database_latency = round((end_database_latency - start_database_latency) * 1000)

        status = "🟢 Отлично" if rest_latency < 300 else "🟠 Медленно"

        await interaction.edit_original_response(content=f"🏓 Понг!\n\n**WebSocket задержка**: `{ws_latency}мс`\n**Реальная задержка** (время между командой и ответом): `{rest_latency}мс`\n**Задержка Базы Данных**: `{database_latency}мс`\n\n**Состояние**: {status}")

    @ping.error
    async def ping_error(self, interaction: discord.Interaction, error):
        _log.error(traceback.format_exc())
        if interaction.response.is_done():
            await interaction.followup.send(embed=discord.Embed(title="❌ Произошла ошибка!", description="Непредвиденная ошибка, прошу связаться с разработчиком", color=0xff0000))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="❌ Произошла ошибка!", description="Непредвиденная ошибка, прошу связаться с разработчиком", color=0xff0000))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(Ping(bot))