import os
import traceback

async def load_all_extensions(bot, base_folder="commands"):
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                relative_path = os.path.join(root, file).replace("\\", "/")
                module = relative_path.removesuffix(".py").replace("/", ".")

                try:
                    await bot.load_extension(module)
                    print(f"✅ Загружено расширение: {module}")
                except Exception as e:
                    print(f"❌ Ошибка при загрузке {module}: {type(e).__name__}: {e}")
                    traceback.print_exc()