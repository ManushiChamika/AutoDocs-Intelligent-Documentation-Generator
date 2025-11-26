from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AutoDocs – Intelligent Documentation Generator"
    environment: str = Field("development", validation_alias="ENVIRONMENT")

    database_url: str = Field(
        "postgresql+psycopg2://autodocs:autodocs@localhost:5432/autodocs",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    model_name: str = Field("gpt-4o-mini", validation_alias="MODEL_NAME")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field("https://api.openrouter.ai/v1", validation_alias="OPENROUTER_BASE_URL")
    # When enabled, bypass LLMs entirely and generate docs from static code analysis.
    safe_mode_no_llm: bool = Field(False, validation_alias="SAFE_MODE_NO_LLM")

    uploads_dir: str = Field("storage/uploads", validation_alias="UPLOADS_DIR")
    artifacts_dir: str = Field("storage/artifacts", validation_alias="ARTIFACTS_DIR")
    download_token: str | None = Field(default=None, validation_alias="DOWNLOAD_TOKEN")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
