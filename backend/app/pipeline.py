"""Processamento de um atendimento: comprimir -> transcrever -> mesclar -> salvar."""

from __future__ import annotations

import logging
from typing import Callable

from . import audio, merge, storage
from .config import Settings
from .db import (
    STATUS_ERRO,
    STATUS_TRANSCRITO,
    STATUS_TRANSCREVENDO,
    Database,
)
from .transcription.base import TranscriptionProvider

log = logging.getLogger("pipeline")


def processar(
    db: Database,
    settings: Settings,
    provider: TranscriptionProvider,
    atendimento_id: int,
    comprimir: Callable = audio.comprimir_para_mp3,
) -> None:
    """Roda em segundo plano. Nunca levanta: falhas viram status 'erro' no banco."""
    atendimento = db.obter(atendimento_id)
    if atendimento is None:
        log.error("Atendimento %s não existe", atendimento_id)
        return

    db.definir_status(atendimento_id, STATUS_TRANSCREVENDO)
    try:
        pasta = settings.data_dir / atendimento["pasta"]
        por_canal = {}
        for canal in storage.CANAIS:
            origem = storage.encontrar_audio(pasta, canal)
            if origem is None:
                continue
            mp3 = pasta / f"{canal}.16k.mp3"
            comprimir(origem, mp3, settings.ffmpeg)
            if atendimento["duracao_segundos"] is None:
                duracao = audio.duracao_segundos(mp3)
                if duracao is not None:
                    db.definir_duracao(atendimento_id, duracao)
                    atendimento["duracao_segundos"] = duracao
            segmentos = provider.transcribe(mp3, settings.language)
            por_canal[canal] = merge.filtrar(segmentos)
            log.info("Atendimento %s: %s -> %d segmentos", atendimento_id, canal, len(por_canal[canal]))

        if not por_canal:
            raise RuntimeError("Nenhum áudio encontrado para este atendimento")

        turnos = merge.agrupar_turnos(merge.mesclar(por_canal))
        db.substituir_segmentos(atendimento_id, turnos)
        db.definir_status(atendimento_id, STATUS_TRANSCRITO)
    except Exception as e:
        log.exception("Falha ao processar atendimento %s", atendimento_id)
        db.definir_status(atendimento_id, STATUS_ERRO, f"{type(e).__name__}: {e}"[:500])
