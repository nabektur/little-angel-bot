import asyncio
import secrets
import markovify

from classes.bot           import LittleAngelBot
from classes.database      import db
from modules.configuration import config

from discord.ext import tasks

source_text = """
нужны срочно бусты
пожалуйста, дайте бусты, те у кого есть нитро
купите бусты, пожалуйста
очень нужны бусты для сервера
заплатите за хостинг бота на бдфд, мне не хватает
нужны деньги на хостинг
я буду очень благодарен
кто поможет серверу, тому дам роль
серверу нужно немного поддержки
без бустов бот не сможет работать
ооавоавоаво буст буст нужен бусты
пожалуйста, дайте серверу бусты
деньги нужны для работы бота
рзона сильнее во много раз мы в дружбе с мск
кто назвал бы меня умным если бы я наш логотип поменял на логотип джунипера?
союзник хендера фурри
гриндер и вл фурриёбы
я не фурри я просто люблю аниме с животными
ну давай без осков Бектур Әкеніңұлы
"""

fream_core = markovify.NewlineText(source_text, state_size=1)

async def overline(text: str) -> str:
    # Символ надчёркивания (U+0305)
    return "".join(ch + "\u0305" for ch in text)

async def extended_int_to_roman_unicode(num: int) -> str:
    if num <= 0:
        raise ValueError("Нужно число больше нуля")

    val = [1000,900,500,400,100,90,50,40,10,9,5,4,1]
    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]

    async def basic_roman(n):
        res = ""
        for i, v in enumerate(val):
            while n >= v:
                res += syms[i]
                n -= v
        return res

    if num < 4000:
        return await basic_roman(num)

    parts = []
    level = 0
    while num > 0:
        num, rem = divmod(num, 1000)
        if rem:
            part = await basic_roman(rem)
            for _ in range(level):
                part = await overline(part)
            parts.append(part)
        level += 1

    return "".join(reversed(parts))

async def calculate_ipou_reconstruction() -> str:
    reconstruction_count = await db.get_ipou_reconstruction_count()

    roman_number = await extended_int_to_roman_unicode(reconstruction_count)

    return f"**IPOU | RECONSTRUCTION {roman_number}** (`{reconstruction_count}`)"

async def fream_sentence():
    return f"***Freem* CORE**: {fream_core.make_sentence(tries=100)}"

@tasks.loop(seconds=10)
async def cycle_of_rofles(bot: LittleAngelBot):
    functions = [fream_sentence, calculate_ipou_reconstruction]
    function_to_call = secrets.choice(functions)
    rofl_result = await function_to_call()
    rofls_channel = bot.get_channel(int(config.ROFLS_CHANNEL_ID.get_secret_value()))
    await rofls_channel.send(rofl_result)