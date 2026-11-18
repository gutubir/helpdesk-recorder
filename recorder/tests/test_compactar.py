import shutil

import pytest

from compactar import ErroCompactacao, comprimir_para_mp3
from conftest import criar_wav

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg não instalado")


def test_comprime_wav_para_mp3_menor(tmp_path):
    wav = criar_wav(tmp_path / "a.wav", segundos=5, taxa=48000)
    mp3 = comprimir_para_mp3(wav, tmp_path / "a.mp3")
    assert mp3.exists() and 0 < mp3.stat().st_size < wav.stat().st_size / 5


def test_arquivo_invalido_levanta_erro(tmp_path):
    ruim = tmp_path / "ruim.wav"
    ruim.write_bytes(b"isso nao e audio")
    with pytest.raises(ErroCompactacao):
        comprimir_para_mp3(ruim, tmp_path / "x.mp3")


def test_ffmpeg_ausente_da_mensagem_clara(tmp_path):
    wav = criar_wav(tmp_path / "a.wav")
    with pytest.raises(ErroCompactacao, match="ffmpeg não encontrado"):
        comprimir_para_mp3(wav, tmp_path / "a.mp3", ffmpeg="ffmpeg-que-nao-existe")
