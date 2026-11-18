"""Une as transcrições dos dois canais em uma conversa única.

Como o microfone é o atendente e o áudio do sistema é o cliente, saber quem
falou não exige modelo de identificação de voz: o canal já diz.
"""

from __future__ import annotations

from typing import Any, Iterable

from .transcription.base import Segment

ROTULOS = {"microfone": "atendente", "sistema": "cliente"}
NOMES_EXIBICAO = {"atendente": "Atendente", "cliente": "Cliente"}


def filtrar(
    segmentos: Iterable[Segment],
    max_no_speech: float = 0.6,
    min_logprob: float = -1.0,
) -> list[Segment]:
    """Remove segmentos vazios e prováveis alucinações em trechos de silêncio.

    As trilhas são preenchidas com silêncio, e o Whisper costuma "inventar"
    texto nesses trechos. Mesma regra do próprio Whisper: descarta quando há
    alta chance de não ser fala E baixa confiança no texto.
    """
    mantidos = []
    for s in segmentos:
        if not s.texto.strip():
            continue
        if (
            s.no_speech_prob is not None
            and s.avg_logprob is not None
            and s.no_speech_prob > max_no_speech
            and s.avg_logprob < min_logprob
        ):
            continue
        mantidos.append(s)
    return mantidos


def mesclar(por_canal: dict[str, list[Segment]]) -> list[dict[str, Any]]:
    """Intercala os segmentos de todos os canais em ordem de tempo."""
    itens = []
    for canal, segmentos in por_canal.items():
        falante = ROTULOS[canal]
        for s in segmentos:
            itens.append(
                {"falante": falante, "inicio": s.inicio, "fim": s.fim, "texto": s.texto.strip()}
            )
    itens.sort(key=lambda i: (i["inicio"], i["fim"], i["falante"]))
    return itens


def agrupar_turnos(itens: list[dict[str, Any]], pausa_max: float = 1.5) -> list[dict[str, Any]]:
    """Junta falas seguidas da mesma pessoa (pausa curta) em um único turno."""
    turnos: list[dict[str, Any]] = []
    for item in itens:
        ultimo = turnos[-1] if turnos else None
        if (
            ultimo
            and ultimo["falante"] == item["falante"]
            and item["inicio"] - ultimo["fim"] <= pausa_max
        ):
            ultimo["fim"] = max(ultimo["fim"], item["fim"])
            ultimo["texto"] = f"{ultimo['texto']} {item['texto']}"
        else:
            turnos.append(dict(item))
    return turnos


def _mmss(segundos: float) -> str:
    total = int(segundos)
    return f"{total // 60:02d}:{total % 60:02d}"


def formatar(turnos: list[dict[str, Any]]) -> str:
    """Texto corrido da conversa, pronto para ler ou enviar à IA do relatório."""
    return "\n".join(
        f"[{_mmss(t['inicio'])}] {NOMES_EXIBICAO.get(t['falante'], t['falante'])}: {t['texto']}"
        for t in turnos
    )
