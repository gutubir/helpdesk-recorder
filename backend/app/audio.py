"""Conversão de áudio com ffmpeg.

O gravador gera WAV na taxa nativa do Windows (~5,5 MB por minuto, por trilha),
grande demais para a API de transcrição (limite de 25 MB por arquivo). Aqui o
áudio vira MP3 mono de 16 kHz (~0,25 MB/min), suficiente para fala.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class ErroAudio(RuntimeError):
    pass


def comprimir_para_mp3(origem: Path, destino: Path, ffmpeg: str = "ffmpeg") -> Path:
    cmd = [
        ffmpeg, "-y", "-v", "error",
        "-i", str(origem),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
        str(destino),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    except FileNotFoundError as e:
        raise ErroAudio(
            "ffmpeg não encontrado. Instale (winget install Gyan.FFmpeg) ou "
            "aponte FFMPEG_PATH no .env."
        ) from e
    except subprocess.CalledProcessError as e:
        detalhe = (e.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ErroAudio(f"ffmpeg falhou ao converter {origem.name}: {detalhe[:300]}") from e
    except subprocess.TimeoutExpired as e:
        raise ErroAudio(f"ffmpeg demorou demais convertendo {origem.name}") from e
    return destino


def duracao_segundos(arquivo: Path, ffprobe: str = "ffprobe") -> Optional[float]:
    """Duração do áudio, ou None se não foi possível medir."""
    cmd = [
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(arquivo),
    ]
    try:
        saida = subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return round(float(saida.stdout.decode().strip()), 1)
    except Exception:
        return None
