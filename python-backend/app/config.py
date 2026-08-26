from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_JWT_SECRET = "dev-only-jwt-secret-change-me-1234567890"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "mysql+pymysql://root:@localhost:3306/collab_doc"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_expiration: int = 86400000  # 24 hours in ms
    allowed_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "granite4.1:8b"
    tavily_api_key: str = ""
    web_search_provider: str = "bing"  # "bing" (free, no key) or "tavily" (falls back to bing without key)
    web_search_timeout: int = 30
    redis_url: str = ""
    realtime_channel_prefix: str = "collab-doc"
    presence_ttl_seconds: int = 45
    rag_vector_backend: str = "local_hash"
    knowledge_max_upload_bytes: int = 10 * 1024 * 1024
    app_env: str = "development"
    auto_create_tables_on_startup: bool = True
    seed_on_startup: bool = True


settings = Settings()
