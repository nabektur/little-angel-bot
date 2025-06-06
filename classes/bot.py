import discord

from discord.ext import commands

class LittleAngelBot(commands.AutoShardedBot):
    async def setup_hook(self):
        from modules.extension_loader import load_all_extensions

        await load_all_extensions(self)

bot_intents = discord.Intents.default()
bot_intents.message_content = True

bot = LittleAngelBot(
    command_prefix="$",
    intents=bot_intents,
    help_command=None,
    activity=discord.Streaming(
        name="ДЕПНУЛ НЕЙМАРА ЗА $500,000!",
        url="https://www.twitch.tv/jasteeq"
    )
)