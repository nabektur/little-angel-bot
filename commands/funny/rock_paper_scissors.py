import secrets

import discord
from discord import app_commands
from discord.ext import commands

from classes.bot import LittleAngelBot
from modules.configuration import config

class RPSWithBot(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder='Ваш вариант', min_values=1, max_values=1, options=[
            discord.SelectOption(label='Камень', description='Выбрать камень', emoji='✊'),
            discord.SelectOption(label='Ножницы', description='Выбрать ножницы', emoji='✌️'),
            discord.SelectOption(label='Бумага', description='Выбрать бумагу', emoji='✋')
        ])

    async def callback(self, interaction: discord.Interaction):
        if self.view.author == interaction.user:
            uvy = self.values[0]
            bvy = secrets.choice(["Камень", "Ножницы", "Бумага"])
            if bvy == "Камень":
                if uvy == "Ножницы":
                    victory = True
                elif uvy == "Бумага":
                    victory = False
                else:
                    victory = None
            elif bvy == "Ножницы":
                if uvy == "Ножницы":
                    victory = None
                elif uvy == "Бумага":
                    victory = True
                else:
                    victory = False
            else:
                if uvy == "Ножницы":
                    victory = False
                elif uvy == "Бумага":
                    victory = None
                else:
                    victory = True

            if victory == True:
                await interaction.response.edit_message(embed=discord.Embed(
                    title="КНБ",
                    description=f"Ваш выбор: `{uvy}`\nМой выбор: `{bvy}`\nЯ победил! 😊",
                    color=config.LITTLE_ANGEL_COLOR
                ), view=None)
            elif victory == False:
                await interaction.response.edit_message(embed=discord.Embed(
                    title="КНБ",
                    description=f"Ваш выбор: `{uvy}`\nМой выбор: `{bvy}`\nПобеда за вами... 🥺",
                    color=config.LITTLE_ANGEL_COLOR
                ), view=None)
            else:
                await interaction.response.edit_message(embed=discord.Embed(
                    title="КНБ",
                    description=f"Ваш выбор: `{uvy}`\nМой выбор: `{bvy}`\nНичья! 🤝",
                    color=config.LITTLE_ANGEL_COLOR
                ), view=None)
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Ошибка! ❌",
                description="Использовать интеграцию может только тот человек, который вызывал команду!",
                color=0xff0000
            ), ephemeral=True)


class RPSWithBotView(discord.ui.View):
    async def on_timeout(self) -> None:
        try:
            message = await self.message.channel.fetch_message(self.message.id)
            if not message.embeds[0].title == "КНБ выбор":
                return
            for item in self.children:
                item.disabled = True
            await message.edit(view=self, embed=discord.Embed(title="КНБ выбор", description="Проигнорили...", color=0x747880))
        except:
            return

    def __init__(self, timeout, author=None, message=None):
        super().__init__()
        self.author: discord.Member = author
        self.message: discord.Message = message
        self.add_item(RPSWithBot())


class RPSWithUser(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder='Ваш вариант', min_values=1, max_values=1, options=[
            discord.SelectOption(label='Камень', description='Выбрать камень', emoji='✊'),
            discord.SelectOption(label='Ножницы', description='Выбрать ножницы', emoji='✌️'),
            discord.SelectOption(label='Бумага', description='Выбрать бумагу', emoji='✋')
        ])

    async def callback(self, interaction: discord.Interaction):
        selected1 = None
        user1 = self.view.user1
        user2 = self.view.user2

        if interaction.user.id not in [user1.id, user2.id]:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Ошибка! ❌",
                description="Вы не участвуете в этой игре!",
                color=0xff0000
            ), ephemeral=True)

        try:
            selected1 = self.view.selected1
        except:
            pass

        if (interaction.user.id == user2.id and selected1 == None) or (interaction.user.id == user1.id and selected1):
            return await interaction.response.send_message(embed=discord.Embed(
                title="Ошибка! ❌",
                description="Сейчас не ваш ход!",
                color=0xff0000
            ), ephemeral=True)

        if not selected1:
            self.view.selected1 = self.values[0]
            await interaction.response.edit_message(embed=discord.Embed(
                title="КНБ выбор",
                description=f"{user1.mention} совершил ход\n{user2.mention} ваша очередь!",
                color=config.LITTLE_ANGEL_COLOR
            ), view=self.view)
        else:
            selected2 = self.values[0]
            if selected1 == "Камень":
                if selected2 == "Ножницы":
                    victory = user1
                elif selected2 == "Бумага":
                    victory = user2
                else:
                    victory = None
            elif selected1 == "Ножницы":
                if selected2 == "Ножницы":
                    victory = None
                elif selected2 == "Бумага":
                    victory = user1
                else:
                    victory = user2
            else:
                if selected2 == "Ножницы":
                    victory = user2
                elif selected2 == "Бумага":
                    victory = None
                else:
                    victory = user1

            if not victory:
                await interaction.response.edit_message(embed=discord.Embed(
                    title="КНБ",
                    description=f"Выбор {user1.mention}: `{selected1}`\nВыбор {user2.mention}: `{selected2}`\nНичья!",
                    color=config.LITTLE_ANGEL_COLOR
                ), view=None)
            else:
                await interaction.response.edit_message(embed=discord.Embed(
                    title="КНБ",
                    description=f"Выбор {user1.mention}: `{selected1}`\nВыбор {user2.mention}: `{selected2}`\nПобедил: {victory.mention}",
                    color=config.LITTLE_ANGEL_COLOR
                ), view=None)


class RPSWithUserView(discord.ui.View):
    async def on_timeout(self) -> None:
        try:
            message = await self.message.channel.fetch_message(self.message.id)
            if not message.embeds[0].title == "КНБ выбор":
                return
            for item in self.children:
                item.disabled = True
            await message.edit(view=self, embed=discord.Embed(title="КНБ выбор", description="Проигнорили...", color=0x747880))
        except:
            return

    def __init__(self, timeout, user1=None, user2=None, message=None):
        super().__init__()
        self.user1: discord.Member = user1
        self.user2: discord.Member = user2
        self.message: discord.Message = message
        self.add_item(RPSWithUser())

class RPS(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot


    @app_commands.command(name='кнб', description='Сыграем в камень-ножницы-бумага?')
    @app_commands.guild_only
    @app_commands.describe(member='Выберите с кем играть')
    async def RPS_command(self, interaction: discord.Interaction, member: discord.Member = None):
        if not member:
            view = RPSWithBotView(timeout=300, author=interaction.user)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="КНБ выбор",
                    description="Хорошо, вы предпочли играть с ботом. Выберите вариант в меню снизу",
                    color=config.LITTLE_ANGEL_COLOR
                ),
                view=view
            )
            view.message = await interaction.original_response()
        else:
            if member.bot:
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Ошибка! ❌",
                    description="Выберите человека, а не бота!",
                    color=0xff0000
                ), ephemeral=True)
            if member == interaction.user:
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Ошибка! ❌",
                    description="Нельзя играть с самим собой!",
                    color=0xff0000
                ), ephemeral=True)

            view = RPSWithUserView(timeout=300)
            ralis = [interaction.user, member]
            view.user1 = secrets.choice(ralis)
            ralis.remove(view.user1)
            view.user2 = ralis[0]

            await interaction.response.send_message(
                content=" ".join([mem.mention for mem in [interaction.user, member]]),
                embed=discord.Embed(
                    title="КНБ выбор",
                    description=f"Начинаем игру!\nХод за {view.user1.mention}",
                    color=config.LITTLE_ANGEL_COLOR
                ),
                view=view
            )
            view.message = await interaction.original_response()

async def setup(bot: LittleAngelBot):
    await bot.add_cog(RPS(bot))