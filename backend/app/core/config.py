import sys

from pydantic_settings import BaseSettings

_ENV_FILE = None if "pytest" in sys.modules else ".env"


class Settings(BaseSettings):
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    COSMOS_DB_ENDPOINT: str = ""
    COSMOS_DB_KEY: str = ""
    COSMOS_DB_DATABASE: str = "emposo-db"
    COSMOS_DB_EMPLOYEES_CONTAINER: str = "employee"

    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_KEY: str = ""
    AZURE_SEARCH_INDEX: str = "cvision-v3-index"
    AZURE_SEARCH_API_VERSION: str = "2024-07-01"

    OPENAI_ENDPOINT: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_API_VERSION: str = "2024-10-21"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_EMBEDDING_DIMENSIONS: int = 3072
    OPENAI_CHAT_MODEL: str = "gpt-4o"

    AZURE_AD_TENANT_ID: str = ""
    AZURE_AD_CLIENT_ID: str = ""

    model_config = {
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
