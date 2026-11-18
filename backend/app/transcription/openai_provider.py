"""Transcrição pela API da OpenAI.

Usa `whisper-1` com `verbose_json`, único formato que devolve segmentos com
tempo (necessário para intercalar as falas do atendente e do cliente). Os
modelos gpt-4o-transcribe não devolvem tempos por segmento.
"""

from __future__ import annotations

from pathlib import Path

from .base import Segment


def _campo(obj, nome, padrao=None):
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "whisper-1"):
        from openai import OpenAI  # import tardio: só exigido se este provedor for usado

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def transcribe(self, audio_path: Path, language: str) -> list[Segment]:
        with open(audio_path, "rb") as f:
            resp = self.client.audio.transcriptions.create(
                model=self.model,
                file=f,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        brutos = _campo(resp, "segments", None) or []
        return [
            Segment(
                inicio=float(_campo(s, "start", 0.0)),
                fim=float(_campo(s, "end", 0.0)),
                texto=str(_campo(s, "text", "")),
                no_speech_prob=_campo(s, "no_speech_prob"),
                avg_logprob=_campo(s, "avg_logprob"),
            )
            for s in brutos
        ]
