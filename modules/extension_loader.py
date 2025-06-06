import os
import logging
import traceback

_log = logging.getLogger(__name__)

from classes.bot import LittleAngelBot

async def load_all_extensions(bot: LittleAngelBot, base_folder="commands"):
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                relative_path = os.path.join(root, file).replace("\\", "/")
                module = relative_path.removesuffix(".py").replace("/", ".")

                try:
                    await bot.load_extension(module)
                    _log.info(f"✅ Загружено расширение: {module}")
                except Exception as e:
                    _log.error(f"❌ Ошибка при загрузке {module}: {type(e).__name__}: {e}")
                    _log.error(traceback.format_exc())