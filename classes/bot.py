import discord

from discord.ext import commands

class LittleAngelBot(commands.AutoShardedBot):
    async def setup_hook(self):
        from modules.extension_loader import load_all_extensions

        await load_all_extensions(self)

discord_intents = discord.Intents.default()
discord_intents.message_content = True

bot = LittleAngelBot(
    command_prefix=commands.when_mentioned_or("$"),
    case_insensitive=True,
    help_command=None,
    intents=discord_intents,
    activity=discord.Streaming(
        name="ДЕПНУЛ НЕЙМАРА ЗА $500,000!",
        url="https://www.twitch.tv/jasteeq"
    )
)