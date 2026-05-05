from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_embed_model: str = "openai/text-embedding-3-small"
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "hr-knowledge"
    kb_path: str = "./knowledge_base"
    top_k_chunks: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
