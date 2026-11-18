import json
import shutil

import pytest

from compactar import ErroCompactacao
from configuracao import PADRAO
from conftest import criar_wav
from envio import MARCADOR, enviar_pasta, enviar_pendentes, pendentes

ffmpeg_ok = shutil.which("ffmpeg") is not None


def _cfg(tmp_path, url, **extra):
    cfg = dict(PADRAO, pasta_saida=tmp_path / "atendimentos", backend_url=url, api_token="tok")
    cfg.update(extra)
    return cfg


def _atendimento(base, nome, canais=("microfone", "sistema"), finalizado=True):
    pasta = base / nome
    for canal in canais:
        criar_wav(pasta / f"{canal}.wav", segundos=1, taxa=16000)
    if finalizado:
        (pasta / "meta.json").write_text(json.dumps({"inicio": "2026-11-18T10:00:00", "duracao_segundos": 1.0}))
    return pasta


def test_pendentes_ignora_enviados_e_nao_finalizados(tmp_path):
    base = tmp_path / "atendimentos"
    a = _atendimento(base, "2026-11-18_10-00-00")
    b = _atendimento(base, "2026-11-18_11-00-00")
    (b / MARCADOR).write_text("{}")
    _atendimento(base, "2026-11-18_12-00-00", finalizado=False)  # gravação em andamento
    assert pendentes(base) == [a]
    assert pendentes(tmp_path / "nao-existe") == []


@pytest.mark.skipif(not ffmpeg_ok, reason="ffmpeg não instalado")
def test_envia_compactado_e_marca_como_enviado(servidor, tmp_path):
    srv = servidor(token_esperado="tok")
    pasta = _atendimento(tmp_path / "atendimentos", "a1")

    resposta = enviar_pasta(pasta, _cfg(tmp_path, srv.url))

    assert resposta["id"] == 7
    partes = srv.recebidos[0]["partes"]
    assert partes["microfone"]["filename"] == "microfone.mp3"
    assert partes["sistema"]["filename"] == "sistema.mp3"
    assert json.loads(partes["meta"]["dados"])["duracao_segundos"] == 1.0
    assert json.loads((pasta / MARCADOR).read_text())["id"] == 7
    assert not (pasta / "microfone.mp3").exists()   # temporário removido
    assert (pasta / "microfone.wav").exists()        # original local preservado


def test_sem_compactar_envia_wav(servidor, tmp_path):
    srv = servidor()
    pasta = _atendimento(tmp_path / "atendimentos", "a1")
    enviar_pasta(pasta, _cfg(tmp_path, srv.url, compactar_antes_de_enviar=False))
    assert srv.recebidos[0]["partes"]["microfone"]["filename"] == "microfone.wav"


def test_ffmpeg_ausente_cai_para_wav(servidor, tmp_path):
    srv = servidor()
    pasta = _atendimento(tmp_path / "atendimentos", "a1", canais=("microfone",))

    def sem_ffmpeg(*_):
        raise ErroCompactacao("ffmpeg não encontrado")

    enviar_pasta(pasta, _cfg(tmp_path, srv.url), comprimir=sem_ffmpeg)
    assert srv.recebidos[0]["partes"]["microfone"]["filename"] == "microfone.wav"


def test_apagar_local_apos_envio(servidor, tmp_path):
    srv = servidor()
    pasta = _atendimento(tmp_path / "atendimentos", "a1")
    enviar_pasta(pasta, _cfg(tmp_path, srv.url, compactar_antes_de_enviar=False, apagar_local_apos_envio=True))
    assert not (pasta / "microfone.wav").exists() and not (pasta / "sistema.wav").exists()
    assert (pasta / "meta.json").exists()


def test_falha_mantem_pendente(servidor, tmp_path):
    srv = servidor(token_esperado="outro")  # token errado -> 401
    pasta = _atendimento(tmp_path / "atendimentos", "a1")
    enviados, falhas = enviar_pendentes(_cfg(tmp_path, srv.url, compactar_antes_de_enviar=False))
    assert (enviados, falhas) == (0, 1)
    assert not (pasta / MARCADOR).exists()
    assert pendentes(tmp_path / "atendimentos") == [pasta]


def test_enviar_pendentes_envia_todos(servidor, tmp_path):
    srv = servidor()
    base = tmp_path / "atendimentos"
    _atendimento(base, "a1")
    _atendimento(base, "a2")
    enviados, falhas = enviar_pendentes(_cfg(tmp_path, srv.url, compactar_antes_de_enviar=False))
    assert (enviados, falhas) == (2, 0)
    assert pendentes(base) == []


def test_backend_fora_do_ar_para_na_primeira_falha(tmp_path):
    base = tmp_path / "atendimentos"
    _atendimento(base, "a1")
    _atendimento(base, "a2")
    enviados, falhas = enviar_pendentes(_cfg(tmp_path, "http://127.0.0.1:1", compactar_antes_de_enviar=False))
    assert (enviados, falhas) == (0, 1)  # não tentou a segunda
