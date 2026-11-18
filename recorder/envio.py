"""Envio dos atendimentos gravados ao backend, com controle de pendentes.

Um atendimento só é considerado enviado quando o backend confirma; nesse caso
a pasta recebe o marcador `enviado.json`. Sem ele, a pasta fica pendente e é
reenviada na próxima inicialização ou pelo menu "Reenviar pendentes".
"""

import json
import logging
from datetime import datetime

from cliente import ErroEnvio, enviar_atendimento
from compactar import ErroCompactacao, comprimir_para_mp3

log = logging.getLogger("envio")

MARCADOR = "enviado.json"
CANAIS = ("microfone", "sistema")


def pendentes(pasta_base):
    """Pastas de atendimento finalizadas (têm meta.json) e ainda não enviadas."""
    if not pasta_base.exists():
        return []
    return sorted(
        p for p in pasta_base.iterdir()
        if p.is_dir() and (p / "meta.json").exists() and not (p / MARCADOR).exists()
    )


def enviar_pasta(pasta, cfg, comprimir=comprimir_para_mp3):
    """Envia uma pasta de atendimento. Devolve a resposta do backend."""
    meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    arquivos, temporarios = {}, []
    try:
        for canal in CANAIS:
            wav = pasta / f"{canal}.wav"
            if not wav.exists():
                continue
            if cfg["compactar_antes_de_enviar"]:
                mp3 = pasta / f"{canal}.mp3"
                try:
                    comprimir(wav, mp3, cfg["ffmpeg"])
                    arquivos[canal] = mp3
                    temporarios.append(mp3)
                    continue
                except ErroCompactacao as e:
                    log.warning("Sem compactar %s (envio do WAV): %s", canal, e)
            arquivos[canal] = wav

        if "microfone" not in arquivos:
            raise ErroEnvio(f"{pasta.name}: microfone.wav não encontrado")

        resposta = enviar_atendimento(
            cfg["backend_url"], cfg["api_token"], arquivos, {"meta": json.dumps(meta, ensure_ascii=False)}
        )
        (pasta / MARCADOR).write_text(
            json.dumps(
                {"id": resposta.get("id"), "enviado_em": datetime.now().isoformat(timespec="seconds")},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    finally:
        for t in temporarios:
            t.unlink(missing_ok=True)

    if cfg["apagar_local_apos_envio"]:
        for canal in CANAIS:
            (pasta / f"{canal}.wav").unlink(missing_ok=True)
    return resposta


def enviar_pendentes(cfg, comprimir=comprimir_para_mp3):
    """Tenta enviar todas as pastas pendentes. Devolve (enviados, falhas)."""
    enviados, falhas = 0, 0
    for pasta in pendentes(cfg["pasta_saida"]):
        try:
            enviar_pasta(pasta, cfg, comprimir)
            enviados += 1
            log.info("Enviado: %s", pasta.name)
        except (ErroEnvio, ErroCompactacao, OSError, ValueError) as e:
            falhas += 1
            log.error("Falha ao enviar %s: %s", pasta.name, e)
            if isinstance(e, ErroEnvio) and e.status is None:
                break  # backend inacessível: não adianta tentar as demais agora
    return enviados, falhas
