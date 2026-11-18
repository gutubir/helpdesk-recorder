import wave
from pathlib import Path

import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "test.db",
        api_token="",
        provider="fake",
        openai_api_key="",
        openai_model="whisper-1",
        language="pt",
        max_upload_mb=5,
        ffmpeg="ffmpeg",
    )


def criar_wav(caminho: Path, segundos: float = 1.0, taxa: int = 16000) -> Path:
    """WAV mono de silêncio, suficiente para testar conversão e upload."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(b"\x00\x00" * int(taxa * segundos))
    return caminho
