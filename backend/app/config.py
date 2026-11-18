"""Configuração lida de variáveis de ambiente (ou do .env, via `uvicorn --env-file .env`).

Tudo que muda entre o PC da empresa e outro ambiente fica aqui, para mover o
backend depois sem mexer no código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path          # onde ficam áudios e o banco
    db_path: Path
    api_token: str          # vazio = sem autenticação (só para localhost!)
    provider: str           # "openai" ou "fake"
    openai_api_key: str
    openai_model: str       # precisa devolver segmentos com tempo: whisper-1
    language: str
    max_upload_mb: int
    ffmpeg: str


def load_settings() -> Settings:
    env = os.environ
    data_dir = Path(env.get("DATA_DIR", "data")).resolve()
    db_path = Path(env.get("DB_PATH", str(data_dir / "helpdesk.db"))).resolve()
    return Settings(
        data_dir=data_dir,
        db_path=db_path,
        api_token=env.get("API_TOKEN", "").strip(),
        provider=env.get("TRANSCRIPTION_PROVIDER", "openai").strip().lower(),
        openai_api_key=env.get("OPENAI_API_KEY", "").strip(),
        openai_model=env.get("OPENAI_TRANSCRIPTION_MODEL", "whisper-1").strip(),
        language=env.get("TRANSCRIPTION_LANGUAGE", "pt").strip(),
        max_upload_mb=int(env.get("MAX_UPLOAD_MB", "300")),
        ffmpeg=env.get("FFMPEG_PATH", "ffmpeg").strip(),
    )
