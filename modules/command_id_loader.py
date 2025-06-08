import typing

from discord import app_commands

from classes.bot import LittleAngelBot

SLASH_COMMAND_IDS = {}

def get_full_command_name(cmd: typing.Union[app_commands.Group, app_commands.Command]):
    parents = []
    parent = cmd.parent
    while parent:
        parents.insert(0, parent.name)
        parent = parent.parent
    return ' '.join(parents + [cmd.name])

async def get_command_id_or_load(bot: LittleAngelBot, name: str) -> int:
    if not SLASH_COMMAND_IDS:
        await load_or_update_command_ids(bot)
    return SLASH_COMMAND_IDS.get(name, 0)

async def load_or_update_command_ids(bot: LittleAngelBot) -> typing.Dict[str, typing.Optional[int]]:

    if SLASH_COMMAND_IDS:
        return SLASH_COMMAND_IDS

    for cmd in bot.tree.get_commands():
        if isinstance(cmd, app_commands.Group):
            for sub in cmd.commands:
                full_name = get_full_command_name(sub)
                if full_name not in SLASH_COMMAND_IDS or not SLASH_COMMAND_IDS[full_name]:
                    SLASH_COMMAND_IDS[full_name] = sub.id
        else:
            full_name = get_full_command_name(cmd)
            if full_name not in SLASH_COMMAND_IDS or not SLASH_COMMAND_IDS[full_name]:
                SLASH_COMMAND_IDS[full_name] = cmd.id

    return SLASH_COMMAND_IDS