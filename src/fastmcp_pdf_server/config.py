from __future__ import annotations

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    max_file_size_mb: int = Field(50)
    log_level: str = Field("INFO")
    log_file_path: str = Field("logs/fastmcp_pdf_server.log")
    temp_dir: str = Field("temp_files")
    server_name: str = Field("pdf-processor-fastmcp")
    server_version: str = Field("1.0.0")

    @field_validator("log_level")
    def _upper(cls, v: str) -> str:  # noqa: N805
        return v.upper()

    @property
    def temp_path(self) -> Path:
        return Path(self.temp_dir).resolve()

    @property
    def log_path(self) -> Path:
        return Path(self.log_file_path).resolve()


settings = Settings()
