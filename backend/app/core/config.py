from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "Orion"

    VERSION: str = "0.1.0"

    DEBUG: bool = True


    class Config:
        env_file = ".env"


settings = Settings()