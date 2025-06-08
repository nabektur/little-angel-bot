import sys
import typing
import dotenv
import discord
import logging

from pydantic          import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = dotenv.find_dotenv()

class Settings(BaseSettings):
    LOGGING_LEVEL: typing.Literal["DEBUG", "INFO", "ERROR", "WARNING", "CRITICAL"] = "INFO"
    DATABASE_URL: SecretStr
    DISCORD_TOKEN: SecretStr
    BOT_LOGS_CHANNEL_ID: SecretStr
    GUILD_ID: SecretStr
    SPAM_SUGGESTIONS_CHANNEL_ID: SecretStr
    LITTLE_ANGEL_COLOR: int = 0x9147ff

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, enable_decoding="utf-8"
    )

config = Settings()

# Логирование
def setup_logging():
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
    )
    
    root_logger.setLevel(config.LOGGING_LEVEL)
    root_logger.addHandler(stdout_handler)
    
    logging.getLogger('discord').setLevel(logging.ERROR)
    logging.getLogger('discord.client').setLevel(logging.ERROR)
    logging.getLogger('discord.gateway').setLevel(logging.ERROR)
    # logging.getLogger('discord.http').setLevel(logging.ERROR)
    logging.getLogger('discord.webhook.async_').setLevel(logging.ERROR)
    
    # logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    return stdout_handler

stdout_handler = setup_logging()