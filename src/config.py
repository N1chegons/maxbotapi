from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    SEARCH_INDEX_1987: str
    SEARCH_INDEX_2010: str
    SEARCH_INDEX_2015: str
    SEARCH_INDEX_2027: str

    MAX_BOT_TOKEN: str

    YC_FOLDER_ID: str
    YC_API_KEY: str

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()