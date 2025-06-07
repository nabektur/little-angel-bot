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

    @discord.ui.button(label="☑️", style=discord.ButtonStyle.blurple, custom_id="spam_suggestion_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        table = "spamtexts_nsfw" if self.spam_type == "nsfw" else "spamtexts_ordinary"
        await db.execute(f"INSERT INTO {table} (text) VALUES ($1) ON CONFLICT DO NOTHING;", self.suggestion)
        await interaction.message.delete()
        await interaction.response.send_message(embed=discord.Embed(description=f"☑️ Текст добавлен в базу ({self.spam_type}).", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger, custom_id="spam_suggestion_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("❌ Текст отклонён.", ephemeral=True)

    @discord.ui.button(label="🚫", style=discord.ButtonStyle.secondary, custom_id="spam_suggestion_block")
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.execute("INSERT INTO blocked_users (user_id, reason) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING;", self.user_id, "Злоупотребление предложкой")
        await interaction.message.delete()
        await interaction.response.send_message("🚫 Пользователь заблокирован.", ephemeral=True)


class SpamSuggestion(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot
        bot.add_view(SuggestSpamView(0, "", "ordinary"))

    suggestion_group = app_commands.Group(
        name="предложка",
        description="Предложите что-либо"
    )

    @suggestion_group.command(name="спам", description="Предложите текст для спама")
    @app_commands.describe(text="Введите текст, который хотите предложить", type="Выберите категорию спама")
    async def suggest_spam(self, interaction: discord.Interaction, text: str, type: typing.Literal["ordinary", "nsfw"]):
        user_id = interaction.user.id

        blocked = await db.fetchone("SELECT * FROM blocked_users WHERE user_id = $1", user_id)
        if blocked:
            return await interaction.response.send_message(embed=discord.Embed(description="❌ Вы заблокированы и не можете предлагать тексты.", color=0xff0000), ephemeral=True)

        embed = discord.Embed(title="✨ Новый предложенный текст для спама", description=text, color=config.LITTLE_ANGEL_COLOR)
        embed.set_footer(text=f"От: {interaction.user} ({user_id}) | Тип: {type}")

        channel = self.bot.get_channel(int(config.SPAM_SUGGESTIONS_CHANNEL_ID.get_secret_value()))
        if channel:
            await channel.send(embed=embed, view=SuggestSpamView(user_id, text, type))

        await interaction.response.send_message(embed=discord.Embed(description="✉️ Предложенный текст отправлен на модерацию!", color=config.LITTLE_ANGEL_COLOR), ephemeral=True)


async def setup(bot: LittleAngelBot):
    await bot.add_cog(SpamSuggestion(bot))
