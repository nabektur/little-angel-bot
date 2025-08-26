import typing
import discord

from discord import app_commands
from discord.ext import commands

from modules.configuration import config

from classes.database import db
from classes.bot      import LittleAngelBot

class SuggestSpamView(discord.ui.View):
    def __init__(self, user_id: int, suggestion: str, spam_type: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.suggestion = suggestion
        self.spam_type = spam_type

    @discord.ui.button(style=discord.ButtonStyle.blurple, custom_id="spam_suggestion_accept", emoji="☑️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        table = "spamtexts_nsfw" if self.spam_type == "nsfw" else "spamtexts_ordinary"
        await db.execute(f"INSERT INTO {table} (text) VALUES (?) ON CONFLICT DO NOTHING;", self.suggestion)
        await interaction.message.delete()
        await interaction.response.send_message(embed=discord.Embed(description=f"☑️ Текст добавлен в базу (`{self.spam_type}`).", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.danger, custom_id="spam_suggestion_reject", emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message(embed=discord.Embed(description="❌ Текст отклонён.", color=0xff0000), ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, custom_id="spam_suggestion_block", emoji="🚫")
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.execute("INSERT INTO blocked_users (user_id, reason) VALUES (?, ?) ON CONFLICT (user_id) DO NOTHING;", self.user_id, "Злоупотребление предложкой")
        await interaction.message.delete()
        await interaction.response.send_message(embed=discord.Embed(description="🚫 Пользователь заблокирован.", color=0xff0000), ephemeral=True)


class SpamSuggestion(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot
        bot.add_view(SuggestSpamView(0, "", "ordinary"))

    suggestion_group = app_commands.Group(
        name="предложка",
        description="Предложите что-либо"
    )

    class SpamSuggestionModal(discord.ui.Modal, title='Кастомный текст'):
        def __init__(self, bot: LittleAngelBot, type: typing.Literal["ordinary", "nsfw"]):
            super().__init__()
            self.bot = bot
            self.type = type

        text = discord.ui.TextInput(
            label='Текст:',
            placeholder='Введите сюда текст, который вы хотите предложить для спама',
            required=True,
            style=discord.TextStyle.long
        )

        async def on_submit(self, interaction: discord.Interaction):
            user_id = interaction.user.id

            blocked = await db.fetchone("SELECT * FROM blocked_users WHERE user_id = ?", user_id)
            if blocked:
                return await interaction.response.send_message(embed=discord.Embed(description="❌ Вы заблокированы и не можете предлагать тексты.", color=0xff0000), ephemeral=True)

            embed = discord.Embed(title="✨ Новый предложенный текст для спама", description=self.text.value, color=config.LITTLE_ANGEL_COLOR)
            embed.set_footer(text=f"От: {interaction.user} ({user_id}) | Тип: {self.type}")

            channel = self.bot.get_channel(int(config.SPAM_SUGGESTIONS_CHANNEL_ID.get_secret_value()))
            if channel:
                await channel.send(embed=embed, view=SuggestSpamView(user_id, self.text.value, self.type))

            await interaction.response.send_message(embed=discord.Embed(description="✉️ Предложенный текст отправлен на модерацию!", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)


    @suggestion_group.command(name="спам", description="Предложите текст для спама")
    @app_commands.choices(type=[app_commands.Choice(name="Спам для обычных каналов", value="ordinary"), app_commands.Choice(name="Спам для nsfw каналов", value="nsfw")])
    @app_commands.describe(type="Выберите категорию спама")
    async def suggest_spam(self, interaction: discord.Interaction, type: typing.Literal["ordinary", "nsfw"]):

        blocked = await db.fetchone("SELECT * FROM blocked_users WHERE user_id = ?", interaction.user.id)
        if blocked:
            return await interaction.response.send_message(embed=discord.Embed(description="❌ Вы заблокированы и не можете предлагать тексты.", color=0xff0000), ephemeral=True)

        modal = self.SpamSuggestionModal(
            bot=self.bot,
            type=type
        )
        return await interaction.response.send_modal(modal)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(SpamSuggestion(bot))
