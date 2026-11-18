"""Provedores de transcrição. Use get_provider(settings) para obter o configurado."""

from .base import Segment, TranscriptionProvider


def get_provider(settings) -> TranscriptionProvider:
    nome = settings.provider
    if nome == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "TRANSCRIPTION_PROVIDER=openai exige OPENAI_API_KEY no .env"
            )
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if nome == "fake":
        from .fake_provider import FakeProvider

        return FakeProvider()
    raise RuntimeError(f"TRANSCRIPTION_PROVIDER desconhecido: {nome!r} (use 'openai' ou 'fake')")


__all__ = ["Segment", "TranscriptionProvider", "get_provider"]
