import discord
import asyncio

from discord.ext import commands

from classes.bot import LittleAngelBot

from modules.configuration  import config

class VoiceVerificationPing(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if str(member.guild.id) == config.GUILD_ID.get_secret_value() and before.channel is None and after.channel and str(after.channel.id) == config.VOICE_VERIFICATION_CHANNEL_ID.get_secret_value():
            verification_channel = await self.bot.fetch_channel(int(config.PING_VERIFICATION_CHANNEL_ID.get_secret_value()))
            await asyncio.sleep(1.5)
            ping_msg = await verification_channel.send(content=member.mention)
            await ping_msg.delete()


async def setup(bot: LittleAngelBot):
    await bot.add_cog(VoiceVerificationPing(bot))
