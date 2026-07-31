from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:@localhost:3306/collab_doc"
    jwt_secret: str = "dev-only-jwt-secret-change-me-1234567890"
    jwt_expiration: int = 86400000  # 24 hours in ms
    allowed_origins: str = "*"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "granite4.1:8b"

    class Config:
        env_file = ".env"


settings = Settings()
