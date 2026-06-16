from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://doclayout:doclayout@localhost:5432/doclayout"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "./uploads"
    result_dir: str = "./results"
    max_pages: int = 50
    result_retention_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
