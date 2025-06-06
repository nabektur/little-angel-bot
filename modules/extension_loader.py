import os
import sys
import logging
import traceback

from modules.configuration import config, stdout_handler

_log = logging.getLogger(__name__)
_log.setLevel(config.LOGGING_LEVEL)
_log.addHandler(stdout_handler)

from classes.bot import LittleAngelBot

async def load_all_extensions(bot: LittleAngelBot, base_folder="commands"):
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                relative_path = os.path.join(root, file).replace("\\", "/")
                module = relative_path.removesuffix(".py").replace("/", ".")

                try:
                    await bot.load_extension(module)
                    logging.info(f"✅ Загружено расширение: {module}")
                except Exception as e:
                    logging.error(f"❌ Ошибка при загрузке {module}: {type(e).__name__}: {e}")
                    logging.error(traceback.format_exc())