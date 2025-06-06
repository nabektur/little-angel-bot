from discord.ext import commands

class LittleAngelBot(commands.AutoShardedBot):
    async def setup_hook(self):
        from modules.extension_loader import load_all_extensions

        await load_all_extensions(self)