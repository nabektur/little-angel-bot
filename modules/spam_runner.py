import random
import typing
import asyncio
import discord
import aiohttp

from datetime import datetime, timezone

from classes.database import db
from classes.bot      import LittleAngelBot

from modules.configuration import config

async def get_spamtexts(texts_type: typing.Literal["ordinary", "nsfw"] = "ordinary"):
    return [row[0] for row in await db.fetch(f"SELECT * FROM spamtexts_{texts_type}")]

async def sync_spam_from_database(bot: LittleAngelBot):
    results = await db.fetch("SELECT * FROM spams")
    [await start_spam_from_database(bot, key) for key in results]

async def start_spam_from_database(bot: LittleAngelBot, key: typing.Tuple):
    try:
        channel = await bot.fetch_channel(key[2])
        if isinstance(channel, discord.Thread):
            wchannel = channel.parent
        else:
            wchannel = channel
        webhooks = await wchannel.webhooks()
        webhook = [webhook for webhook in webhooks if(webhook.name == "Ангелочек")]
        if webhook:
            webhook = webhook[0]
        else:
            webhook = await wchannel.create_webhook(name="Ангелочек", avatar=await bot.user.avatar.read())
    except:
        return

    if key[4]:
        duration = datetime.fromtimestamp(int(key[4]), timezone.utc)
        if datetime.now(timezone.utc) >= duration:
            await db.execute("DELETE FROM spams WHERE channel_id = $1;", channel.id)
            await channel.send("Спам остановлен по причине длительности! ☑️")
            return
        task = asyncio.create_task(run_spam(key[0], key[1], channel, webhook, key[3], duration))
    else:
        task = asyncio.create_task(run_spam(key[0], key[1], channel, webhook, key[3], key[4]))

    task.name = "Автоспам"
    task.channel_id = channel.id

async def check_sp(channel_id):
    return await db.fetchone("SELECT channel_id FROM spams WHERE channel_id = $1", channel_id) != None


async def run_spam(type: str, method: str, channel, webhook, ments=None, duration=None):

    if type == "default":
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.VoiceChannel):
            stexts = await get_spamtexts("nsfw") if channel.is_nsfw() else await get_spamtexts("ordinary")
        else:
            stexts = await get_spamtexts("ordinary")
    else:
        stexts = [stext.strip() for stext in type.split("|")]

    thread = channel if isinstance(channel, discord.Thread) else None

    try:
        while await check_sp(channel.id):
            if duration and datetime.now(timezone.utc) >= duration:
                await db.execute("DELETE FROM spams WHERE channel_id = $1;", channel.id)
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
        await db.execute("DELETE FROM spams WHERE channel_id = $1;", channel.id)
    except discord.errors.HTTPException:
        await asyncio.sleep(3)
    except (discord.errors.DiscordServerError, aiohttp.ClientOSError, aiohttp.ServerDisconnectedError):
        await db.execute("DELETE FROM spams WHERE channel_id = $1;", channel.id)
        await channel.send(embed=discord.Embed(
            title='⚠️ Спам остановлен!',
            color=0xfcb603,
            timestamp=datetime.now(timezone.utc),
            description='Причина: Ошибка сервера Discord'
        ))