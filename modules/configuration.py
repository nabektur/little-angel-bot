import sys
import typing
import dotenv
import logging

from pydantic          import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = dotenv.find_dotenv()

class Settings(BaseSettings):
    LOGGING_LEVEL: typing.Literal["DEBUG", "INFO", "ERROR", "WARNING", "CRITICAL"] = "INFO"
    DATABASE_URL: SecretStr
    DISCORD_TOKEN: SecretStr
    CHANNEL_ID: SecretStr

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, enable_decoding="utf-8"
    )

config = Settings()

# Логирование
stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'))