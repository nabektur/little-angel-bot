import discord

from discord.ext import commands

from modules.configuration import config

class LittleAngelBot(commands.AutoShardedBot):
    async def setup_hook(self):
        from modules.extension_loader import load_all_extensions

        await load_all_extensions(self)
        await load_all_extensions(self, "listeners")

discord_intents = discord.Intents.default()
discord_intents.message_content = True

bot = LittleAngelBot(
    command_prefix=commands.when_mentioned_or("."),
    case_insensitive=True,
    help_command=None,
    intents=discord_intents,
    status=discord.Status.idle,
    activity=discord.Streaming(
        name=config.ACTIVITY_NAME,
        url=config.STREAMING_URL
    )
)