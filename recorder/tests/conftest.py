import wave
from pathlib import Path


def criar_wav(caminho, segundos=1.0, taxa=16000):
    """WAV mono de silêncio, suficiente para testar compactação e envio."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(b"\x00\x00" * int(taxa * segundos))
    return caminho
