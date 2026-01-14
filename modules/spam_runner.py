import asyncio
from datetime import datetime, timezone
import logging
import secrets
import typing

import discord

from classes.bot import LittleAngelBot
from classes.database import db
from modules.configuration import config

LOGGER = logging.getLogger(__name__)

async def get_spamtexts(texts_type: typing.Literal["ordinary", "nsfw"] = "ordinary"):
    return [row[0] for row in await db.fetch(f"SELECT * FROM spamtexts_{texts_type}")]

async def sync_spam_from_database(bot: LittleAngelBot):
    results = await db.fetch("SELECT * FROM spams")
    [await start_spam_from_database(bot, key) for key in results]

async def start_spam_from_database(bot: LittleAngelBot, key: typing.Tuple):
    try:
        channel = await bot.fetch_channel(key[2])
        if key[1] == "webhook":
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
        else:
            webhook = None
    except:
        return

    if key[5]:
        duration = datetime.fromtimestamp(int(key[5]), timezone.utc)
        if datetime.now(timezone.utc) >= duration:
            await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)
            await channel.send(embed=discord.Embed(description="☑️ Спам остановлен по причине длительности!", color=config.LITTLE_ANGEL_COLOR))
            return
        asyncio.create_task(run_spam(key[0], key[1], channel, webhook, key[4], duration))
    else:
        asyncio.create_task(run_spam(key[0], key[1], channel, webhook, key[4], key[5]))

async def check_sp(channel_id):
    return await db.fetchone("SELECT channel_id FROM spams WHERE channel_id = $1 LIMIT 1", channel_id) != None


async def run_spam(type: str, method: str, channel, webhook: discord.Webhook=None, ments=None, duration=None):

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
                await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)
                await channel.send(embed=discord.Embed(description="☑️ Спам остановлен по причине длительности!", color=config.LITTLE_ANGEL_COLOR))
                break

            text = secrets.choice(stexts)
            if ments:
                text = f"{ments}\n{text}"

            if method == "webhook":
                await webhook.send(wait=False, content=text, thread=thread) if thread else await webhook.send(wait=False, content=text)
            else:
                await channel.send(content=text)

            await asyncio.sleep(2)

    except discord.errors.HTTPException:
        await asyncio.sleep(3)
        asyncio.create_task(run_spam(type, method, channel, webhook, ments, duration))

    except discord.errors.NotFound:
        await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)

    except discord.errors.Forbidden:
        await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)
        try:
            await channel.send(embed=discord.Embed(
                title='⚠️ Спам остановлен!',
                color=0xfcb603,
                timestamp=datetime.now(timezone.utc),
                description='Причина: нет прав'
            ))
        except discord.errors.Forbidden:
            pass

    except Exception as e:
        LOGGER.error(f"Error occurred in run_spam: {e}")
        await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)
        await channel.send(embed=discord.Embed(
            title='⚠️ Спам остановлен!',
            color=0xfcb603,
            timestamp=datetime.now(timezone.utc),
            description='Причина: неизвестная ошибка'
        ))

    # except (discord.errors.DiscordServerError, aiohttp.ClientOSError, aiohttp.ServerDisconnectedError):
    #     await db.execute("DELETE FROM spams WHERE channel_id = ?;", channel.id)
    #     await channel.send(embed=discord.Embed(
    #         title='⚠️ Спам остановлен!',
    #         color=0xfcb603,
    #         timestamp=datetime.now(timezone.utc),
    #         description='Причина: Ошибка сервера Discord'
    #     ))