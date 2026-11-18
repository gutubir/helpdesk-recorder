"""Compactação do áudio antes do envio (ffmpeg).

O WAV do gravador tem ~5,5 MB/min por trilha. Convertido para MP3 mono de
16 kHz (suficiente para fala) fica em ~0,25 MB/min, o que torna o envio rápido
mesmo por VPN e evita estourar o limite de 25 MB da API de transcrição.
"""

import subprocess
from pathlib import Path


class ErroCompactacao(RuntimeError):
    pass


def comprimir_para_mp3(origem, destino, ffmpeg="ffmpeg"):
    origem, destino = Path(origem), Path(destino)
    cmd = [
        ffmpeg, "-y", "-v", "error",
        "-i", str(origem),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
        str(destino),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    except FileNotFoundError as e:
        raise ErroCompactacao(
            "ffmpeg não encontrado. Instale (winget install Gyan.FFmpeg) "
            "ou informe o caminho em 'ffmpeg' no config.json."
        ) from e
    except subprocess.CalledProcessError as e:
        detalhe = (e.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ErroCompactacao(f"ffmpeg falhou em {origem.name}: {detalhe[:300]}") from e
    except subprocess.TimeoutExpired as e:
        raise ErroCompactacao(f"ffmpeg demorou demais em {origem.name}") from e
    return destino
