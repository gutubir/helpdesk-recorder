import io

import pytest

from app import storage


def test_salva_com_nome_gerado_e_ignora_nome_do_cliente(tmp_path):
    destino = storage.salvar_upload(
        io.BytesIO(b"dados"), "../../etc/passwd.WAV", tmp_path / "a", "microfone", 1024
    )
    assert destino == tmp_path / "a" / "microfone.wav"
    assert destino.read_bytes() == b"dados"


@pytest.mark.parametrize("nome", ["virus.exe", "semextensao", None, "x.py"])
def test_recusa_extensao_nao_permitida(tmp_path, nome):
    with pytest.raises(storage.UploadInvalido):
        storage.salvar_upload(io.BytesIO(b"x"), nome, tmp_path, "sistema", 1024)


def test_recusa_arquivo_grande_e_nao_deixa_resto(tmp_path):
    with pytest.raises(storage.UploadInvalido) as e:
        storage.salvar_upload(io.BytesIO(b"x" * 2048), "a.wav", tmp_path, "microfone", 1024)
    assert e.value.status_http == 413
    assert not (tmp_path / "microfone.wav").exists()


def test_recusa_arquivo_vazio(tmp_path):
    with pytest.raises(storage.UploadInvalido):
        storage.salvar_upload(io.BytesIO(b""), "a.wav", tmp_path, "microfone", 1024)
    assert not (tmp_path / "microfone.wav").exists()


def test_canal_invalido(tmp_path):
    with pytest.raises(ValueError):
        storage.salvar_upload(io.BytesIO(b"x"), "a.wav", tmp_path, "outro", 1024)


def test_encontrar_audio(tmp_path):
    assert storage.encontrar_audio(tmp_path, "microfone") is None
    (tmp_path / "microfone.mp3").write_bytes(b"x")
    assert storage.encontrar_audio(tmp_path, "microfone") == tmp_path / "microfone.mp3"
    assert storage.encontrar_audio(tmp_path, "sistema") is None
