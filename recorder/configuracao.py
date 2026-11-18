"""Leitura da configuração do gravador.

Ordem (a última vence): padrões -> config.json -> config.local.json -> variável
de ambiente HELPDESK_API_TOKEN. O token fica no config.local.json (ignorado
pelo Git) ou na variável de ambiente, nunca no config.json versionado.
"""

import json
import os
from pathlib import Path

PADRAO = {
    "pasta_saida": "atendimentos",
    "atalho": "ctrl+alt+r",
    "backend_url": "http://localhost:8000",
    "api_token": "",
    "enviar_automaticamente": True,
    "compactar_antes_de_enviar": True,
    "apagar_local_apos_envio": False,
    "ffmpeg": "ffmpeg",
}


def carregar_config(base_dir):
    base_dir = Path(base_dir)
    cfg = dict(PADRAO)
    for nome in ("config.json", "config.local.json"):
        arquivo = base_dir / nome
        if arquivo.exists():
            cfg.update(json.loads(arquivo.read_text(encoding="utf-8")))
    token_env = os.environ.get("HELPDESK_API_TOKEN")
    if token_env:
        cfg["api_token"] = token_env.strip()
    pasta = Path(cfg["pasta_saida"])
    if not pasta.is_absolute():
        pasta = base_dir / pasta
    cfg["pasta_saida"] = pasta
    return cfg
