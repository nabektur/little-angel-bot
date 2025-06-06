import discord
from discord import app_commands
from discord.ext import commands
import time

from modules.bot_class import LittleAngelBot

class Ping(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @app_commands.command(name="пинг", description="Показывает задержку бота")
    async def ping(self, interaction: discord.Interaction):
        start = time.monotonic()

        await interaction.response.send_message("🏓 Считаю пинг...")

        end = time.monotonic()

        ws_latency = round(self.bot.latency * 1000)
        rest_latency = round((end - start) * 1000)

        status = "🟢 Отлично" if rest_latency < 300 else "🟠 Медленно"

        await interaction.edit_original_response(content=f"🏓 Понг!\n\n**WebSocket задержка**: `{ws_latency}мс`\n**Реальная задержка** (время между командой и ответом): `{rest_latency}мс`\n\n**Состояние**: {status}")

async def setup(bot: LittleAngelBot):
    await bot.add_cog(Ping(bot))