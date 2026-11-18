"""Cliente HTTP do backend (somente biblioteca padrão).

Envia o multipart em streaming: o arquivo é lido em blocos e nunca carregado
inteiro na memória, o que importa se for preciso mandar WAV de ligações longas.
"""

import http.client
import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

BLOCO = 1024 * 1024


class ErroEnvio(RuntimeError):
    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.status = status


def _cabecalho_campo(boundary, nome):
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{nome}"\r\n\r\n'
    ).encode("utf-8")


def _cabecalho_arquivo(boundary, nome, arquivo: Path):
    nome_arquivo = arquivo.name.replace('"', "")
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{nome}"; filename="{nome_arquivo}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")


def enviar_atendimento(base_url, token, arquivos, campos=None, timeout=600):
    """POST /atendimentos. `arquivos` = {"microfone": Path, "sistema": Path}.

    Devolve o JSON da resposta (ex.: {"id": 3, "status": "recebido"}).
    Levanta ErroEnvio em falha de rede ou resposta de erro do servidor.
    """
    partes = urlsplit(base_url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ErroEnvio(f"backend_url inválida: {base_url!r}")

    boundary = uuid.uuid4().hex
    blocos = []  # lista de bytes (cabeçalhos) ou Path (conteúdo a ler em streaming)
    for nome, valor in (campos or {}).items():
        blocos += [_cabecalho_campo(boundary, nome), str(valor).encode("utf-8"), b"\r\n"]
    for nome, arquivo in arquivos.items():
        arquivo = Path(arquivo)
        blocos += [_cabecalho_arquivo(boundary, nome, arquivo), arquivo, b"\r\n"]
    blocos.append(f"--{boundary}--\r\n".encode("utf-8"))

    tamanho = sum(os.path.getsize(b) if isinstance(b, Path) else len(b) for b in blocos)

    classe = http.client.HTTPSConnection if partes.scheme == "https" else http.client.HTTPConnection
    conn = classe(partes.hostname, partes.port, timeout=timeout)
    caminho = (partes.path.rstrip("/") or "") + "/atendimentos"
    try:
        conn.putrequest("POST", caminho)
        conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        conn.putheader("Content-Length", str(tamanho))
        if token:
            conn.putheader("Authorization", f"Bearer {token}")
        conn.endheaders()
        for bloco in blocos:
            if isinstance(bloco, Path):
                with open(bloco, "rb") as f:
                    while True:
                        dados = f.read(BLOCO)
                        if not dados:
                            break
                        conn.send(dados)
            else:
                conn.send(bloco)
        resposta = conn.getresponse()
        corpo = resposta.read()
    except (OSError, http.client.HTTPException) as e:
        raise ErroEnvio(f"Não consegui falar com o backend em {base_url}: {e}") from e
    finally:
        conn.close()

    try:
        dados = json.loads(corpo.decode("utf-8")) if corpo else {}
    except ValueError:
        dados = {}
    if not 200 <= resposta.status < 300:
        detalhe = dados.get("detail") if isinstance(dados, dict) else None
        raise ErroEnvio(
            f"Backend recusou o envio (HTTP {resposta.status}): {detalhe or corpo[:200]!r}",
            status=resposta.status,
        )
    return dados
