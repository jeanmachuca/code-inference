from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    inference_url: str = "http://inference:8080"
    rate_limit_per_minute: int = 30
    max_prompt_chars: int = 8000


settings = Settings()
