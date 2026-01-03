import ast
import discord

from discord.ext           import commands

from classes.bot           import LittleAngelBot
from classes.database      import db

from modules.configuration import config

def insert_returns(body):
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)

class ExecuteCode(commands.Cog):
    def __init__(self, bot: LittleAngelBot):
        self.bot = bot

    @commands.command(name="run", description="Запустить команду", guild=discord.Object(id=config.GUILD_ID))
    @commands.is_owner()
    async def run(self, ctx: commands.Context, *, cmd: str):
        fn_name = "_eval_expr"
        cmd = cmd.strip("` ")
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"
        parsed = ast.parse(body)
        body = parsed.body[0].body
        insert_returns(body)
        env = {
            'bot': self.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__,
            'db': db,
            'config': config
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)
        await eval(f"{fn_name}()", env)
        await ctx.reply(embed=discord.Embed(
            description="☑️ Команда выполнена!", 
            color=config.LITTLE_ANGEL_COLOR
        ))

    @run.error
    async def run_error(self, ctx: commands.Context, error):
        return await ctx.reply(embed=discord.Embed(title="❌ Произошла ошибка!", color=0xff0000, description=f"```py\n{error}```"))

async def setup(bot: LittleAngelBot):
    await bot.add_cog(ExecuteCode(bot))