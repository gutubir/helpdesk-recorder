"""Provedor de mentira, para desenvolver e testar sem gastar API.

Ative com TRANSCRIPTION_PROVIDER=fake. Devolve sempre um trecho fixo, com o
nome do arquivo no texto, só para ver o fluxo completo funcionando.
"""

from __future__ import annotations

from pathlib import Path

from .base import Segment


class FakeProvider:
    def transcribe(self, audio_path: Path, language: str) -> list[Segment]:
        return [Segment(0.0, 2.0, f"[teste] trecho de {Path(audio_path).name}")]
