from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'dispatch.db'}"
    vertex_ai: bool = False
    vertex_ai_api_key: str = ""
    vertex_ai_project: str = "tmi-project-497809"
    vertex_ai_location: str = "global"
    gemini_model: str = "gemini-2.5-pro"
    cors_origins: list[str] = ["http://localhost:3000"]
    scoring_weights: dict[str, float] = {
        "customer_preference": 20.0,
        "similar_job_experience": 15.0,
        "hour_balancing": 25.0,
        "cost_efficiency": 10.0,
        "skill_match": 30.0,
    }
    min_crew_score_threshold: float = 40.0
    optimization_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
