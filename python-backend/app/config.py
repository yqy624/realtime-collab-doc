from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:@localhost:3306/collab_doc"
    jwt_secret: str = "dev-only-jwt-secret-change-me-1234567890"
    jwt_expiration: int = 86400000  # 24 hours in ms
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
