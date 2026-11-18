"""Armazenamento dos áudios enviados.

Os nomes dos arquivos são sempre gerados aqui (canal + extensão validada);
nada do nome enviado pelo cliente vai para o caminho no disco.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Optional

CANAIS = ("microfone", "sistema")
EXTENSOES_PERMITIDAS = {".wav", ".mp3", ".opus", ".ogg", ".m4a", ".flac", ".webm"}
_BLOCO = 1024 * 1024


class UploadInvalido(Exception):
    """Arquivo recusado (extensão não permitida ou grande demais)."""

    def __init__(self, mensagem: str, status_http: int = 400):
        super().__init__(mensagem)
        self.status_http = status_http


def pasta_do_atendimento(data_dir: Path, atendimento_id: int) -> Path:
    return data_dir / "atendimentos" / f"{atendimento_id:06d}"


def salvar_upload(
    arquivo: BinaryIO,
    nome_original: Optional[str],
    pasta: Path,
    canal: str,
    max_bytes: int,
) -> Path:
    if canal not in CANAIS:
        raise ValueError(f"canal inválido: {canal}")
    ext = Path(nome_original or "").suffix.lower()
    if ext not in EXTENSOES_PERMITIDAS:
        raise UploadInvalido(
            f"Arquivo de {canal} com extensão não permitida ({ext or 'sem extensão'}). "
            f"Use: {', '.join(sorted(EXTENSOES_PERMITIDAS))}"
        )
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{canal}{ext}"
    total = 0
    try:
        with open(destino, "wb") as saida:
            while True:
                bloco = arquivo.read(_BLOCO)
                if not bloco:
                    break
                total += len(bloco)
                if total > max_bytes:
                    raise UploadInvalido(
                        f"Arquivo de {canal} maior que o limite de {max_bytes // (1024 * 1024)} MB",
                        status_http=413,
                    )
                saida.write(bloco)
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    if total == 0:
        destino.unlink(missing_ok=True)
        raise UploadInvalido(f"Arquivo de {canal} está vazio")
    return destino


def encontrar_audio(pasta: Path, canal: str) -> Optional[Path]:
    """Áudio original recebido para o canal (qualquer extensão permitida)."""
    for ext in sorted(EXTENSOES_PERMITIDAS):
        candidato = pasta / f"{canal}{ext}"
        if candidato.exists():
            return candidato
    return None
