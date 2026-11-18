"""Contrato dos provedores de transcrição.

Para trocar de OpenAI para faster-whisper local (ou outro), basta criar uma
classe com o método `transcribe` e registrá-la em `get_provider`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass(frozen=True)
class Segment:
    inicio: float                      # segundos desde o começo do áudio
    fim: float
    texto: str
    no_speech_prob: Optional[float] = None   # usados para descartar alucinações
    avg_logprob: Optional[float] = None      # do modelo em trechos de silêncio


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> list[Segment]:
        """Transcreve um arquivo de áudio e devolve segmentos com tempo."""
        ...
