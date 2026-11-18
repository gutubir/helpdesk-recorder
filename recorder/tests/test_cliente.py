import pytest

from cliente import ErroEnvio, enviar_atendimento


def test_envia_arquivos_e_campos(servidor, tmp_path):
    srv = servidor()
    mic = tmp_path / "microfone.mp3"
    sis = tmp_path / "sistema.mp3"
    mic.write_bytes(b"AUDIO-MIC" * 1000)
    sis.write_bytes(b"AUDIO-SIS" * 1000)

    r = enviar_atendimento(srv.url, "", {"microfone": mic, "sistema": sis}, {"meta": '{"inicio": "x"}'})

    assert r == {"id": 7, "status": "recebido"}
    recebido = srv.recebidos[0]
    assert recebido["caminho"] == "/atendimentos"
    assert recebido["partes"]["microfone"]["dados"] == b"AUDIO-MIC" * 1000
    assert recebido["partes"]["microfone"]["filename"] == "microfone.mp3"
    assert recebido["partes"]["sistema"]["dados"] == b"AUDIO-SIS" * 1000
    assert recebido["partes"]["meta"]["dados"] == b'{"inicio": "x"}'


def test_envia_arquivo_grande_em_blocos(servidor, tmp_path):
    srv = servidor()
    grande = tmp_path / "microfone.wav"
    grande.write_bytes(b"\x01" * (3 * 1024 * 1024 + 17))  # mais de 3 blocos
    enviar_atendimento(srv.url, "", {"microfone": grande})
    assert srv.recebidos[0]["partes"]["microfone"]["dados"] == grande.read_bytes()


def test_token_correto_e_errado(servidor, tmp_path):
    srv = servidor(token_esperado="segredo")
    mic = tmp_path / "microfone.mp3"
    mic.write_bytes(b"x")
    assert enviar_atendimento(srv.url, "segredo", {"microfone": mic})["id"] == 7
    with pytest.raises(ErroEnvio) as e:
        enviar_atendimento(srv.url, "errado", {"microfone": mic})
    assert e.value.status == 401
    assert "Token inválido" in str(e.value)


def test_erro_do_servidor_mostra_detalhe(servidor, tmp_path):
    srv = servidor(status=413, resposta={"detail": "Arquivo grande demais"})
    mic = tmp_path / "microfone.mp3"
    mic.write_bytes(b"x")
    with pytest.raises(ErroEnvio, match="Arquivo grande demais") as e:
        enviar_atendimento(srv.url, "", {"microfone": mic})
    assert e.value.status == 413


def test_backend_fora_do_ar(tmp_path):
    mic = tmp_path / "microfone.mp3"
    mic.write_bytes(b"x")
    with pytest.raises(ErroEnvio, match="Não consegui falar com o backend") as e:
        enviar_atendimento("http://127.0.0.1:1", "", {"microfone": mic}, timeout=2)
    assert e.value.status is None


def test_url_invalida(tmp_path):
    with pytest.raises(ErroEnvio, match="inválida"):
        enviar_atendimento("localhost:8000", "", {})
