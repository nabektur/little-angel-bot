import asyncio
import random
import discord
import aiohttp
from datetime import datetime, timezone

from classes.database import db
from modules.configuration import config

async def check_sp(channel_id):
    return await db.fetchone("SELECT channel_id FROM spams WHERE channel_id = $1", (channel_id,)) != None


async def run_spam(type: str, method: str, channel, webhook, ments=None, duration=None):

    if type == "default":
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.VoiceChannel):
            stexts = config.SPAMTEXTS_NSFW if channel.is_nsfw() else config.SPAMTEXTS_ORDINARY
        else:
            stexts = config.SPAMTEXTS_ORDINARY
    else:
        stexts = [stext.strip() for stext in type.split("|")]

    thread = channel if isinstance(channel, discord.Thread) else None

    try:
        while await check_sp(channel.id):
            if duration and datetime.now(timezone.utc) >= duration:
                await db.execute("DELETE FROM spams WHERE channel_id = $1;", (channel.id,))
                await channel.send("Спам остановлен по причине длительности! ☑️")
                break

            text = random.choice(stexts)
            if ments:
                text = f"{ments}\n{text}"

            if method == "webhook":
                await webhook.send(wait=True, content=text, thread=thread) if thread else await webhook.send(wait=True, content=text)
            else:
                await channel.send(content=text)

    except discord.errors.NotFound:
        await db.execute("DELETE FROM spams WHERE channel_id = $1;", (channel.id,))
    except discord.errors.HTTPException:
        await asyncio.sleep(3)
    except (discord.errors.DiscordServerError, aiohttp.ClientOSError, aiohttp.ServerDisconnectedError):
        await db.execute("DELETE FROM spams WHERE channel_id = $1;", (channel.id,))
        await channel.send(embed=discord.Embed(
            title='⚠️ Спам остановлен!',
            color=0xfcb603,
            timestamp=datetime.now(timezone.utc),
            description='Причина: Ошибка сервера Discord'
        ))