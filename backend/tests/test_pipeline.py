"""Testa o fluxo completo (ffmpeg real, transcrição simulada)."""

import shutil

import pytest

from app import pipeline, storage
from app.db import STATUS_ERRO, STATUS_TRANSCRITO, Database
from app.transcription.base import Segment
from app.transcription.fake_provider import FakeProvider

from conftest import criar_wav

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg não instalado")


class ProvedorPorCanal:
    """Devolve falas diferentes conforme o canal (pelo nome do arquivo)."""

    def transcribe(self, audio_path, language):
        if audio_path.name.startswith("microfone"):
            return [Segment(0.0, 1.0, "Suporte, bom dia"), Segment(1.0, 2.0, "silêncio", 0.95, -2.0)]
        return [Segment(3.0, 4.0, "Minha nota foi rejeitada")]


def _novo_atendimento(settings, db, canais=("microfone", "sistema")):
    i = db.criar_atendimento()
    pasta = storage.pasta_do_atendimento(settings.data_dir, i)
    db.definir_pasta(i, str(pasta.relative_to(settings.data_dir)))
    for canal in canais:
        criar_wav(pasta / f"{canal}.wav", segundos=1.0)
    return i


def test_processa_atendimento_completo(settings):
    db = Database(settings.db_path)
    i = _novo_atendimento(settings, db)

    pipeline.processar(db, settings, ProvedorPorCanal(), i)

    a = db.obter(i)
    assert a["status"] == STATUS_TRANSCRITO, a["erro"]
    assert a["duracao_segundos"] is not None and a["duracao_segundos"] > 0
    turnos = db.listar_segmentos(i)
    assert [(t["falante"], t["texto"]) for t in turnos] == [
        ("atendente", "Suporte, bom dia"),   # "silêncio" foi filtrado
        ("cliente", "Minha nota foi rejeitada"),
    ]
    pasta = settings.data_dir / a["pasta"]
    assert (pasta / "microfone.16k.mp3").stat().st_size > 0
    assert (pasta / "microfone.wav").exists()  # original preservado


def test_aceita_atendimento_so_com_microfone(settings):
    db = Database(settings.db_path)
    i = _novo_atendimento(settings, db, canais=("microfone",))
    pipeline.processar(db, settings, FakeProvider(), i)
    assert db.obter(i)["status"] == STATUS_TRANSCRITO
    assert [t["falante"] for t in db.listar_segmentos(i)] == ["atendente"]


def test_falha_do_provedor_vira_status_erro(settings):
    class Quebrado:
        def transcribe(self, *_):
            raise RuntimeError("API fora do ar")

    db = Database(settings.db_path)
    i = _novo_atendimento(settings, db)
    pipeline.processar(db, settings, Quebrado(), i)
    a = db.obter(i)
    assert a["status"] == STATUS_ERRO
    assert "API fora do ar" in a["erro"]


def test_sem_audio_vira_erro(settings):
    db = Database(settings.db_path)
    i = _novo_atendimento(settings, db, canais=())
    pipeline.processar(db, settings, FakeProvider(), i)
    assert db.obter(i)["status"] == STATUS_ERRO


def test_atendimento_inexistente_nao_levanta(settings):
    pipeline.processar(Database(settings.db_path), settings, FakeProvider(), 999)
