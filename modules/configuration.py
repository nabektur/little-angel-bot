import dotenv

from pydantic          import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = dotenv.find_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: SecretStr
    DISCORD_TOKEN: SecretStr
    CHANNEL_ID: SecretStr

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, enable_decoding="utf-8"
    )

settings = Settings()