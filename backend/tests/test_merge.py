from app import merge
from app.transcription.base import Segment


def test_filtrar_remove_vazios_e_alucinacoes():
    segs = [
        Segment(0, 1, "  "),                                              # vazio
        Segment(1, 2, "Legendas pela comunidade", 0.9, -1.5),             # silêncio inventado
        Segment(2, 3, "Bom dia, suporte", 0.1, -0.2),                     # fala real
        Segment(3, 4, "texto incerto mas com fala", 0.9, -0.3),           # só um critério: mantém
        Segment(4, 5, "sem metadados"),                                   # sem probabilidades: mantém
    ]
    textos = [s.texto for s in merge.filtrar(segs)]
    assert textos == ["Bom dia, suporte", "texto incerto mas com fala", "sem metadados"]


def test_mesclar_intercala_por_tempo_e_rotula_canais():
    por_canal = {
        "microfone": [Segment(0.0, 2.0, "Suporte, bom dia"), Segment(6.0, 8.0, "Vou verificar")],
        "sistema": [Segment(2.5, 5.0, "Minha nota foi rejeitada")],
    }
    itens = merge.mesclar(por_canal)
    assert [(i["falante"], i["texto"]) for i in itens] == [
        ("atendente", "Suporte, bom dia"),
        ("cliente", "Minha nota foi rejeitada"),
        ("atendente", "Vou verificar"),
    ]


def test_agrupar_turnos_junta_falas_proximas_do_mesmo_falante():
    itens = [
        {"falante": "cliente", "inicio": 0.0, "fim": 2.0, "texto": "Oi"},
        {"falante": "cliente", "inicio": 2.5, "fim": 4.0, "texto": "tudo bem?"},
        {"falante": "atendente", "inicio": 4.2, "fim": 5.0, "texto": "Tudo."},
        {"falante": "cliente", "inicio": 10.0, "fim": 11.0, "texto": "Preciso de ajuda"},  # pausa longa
    ]
    turnos = merge.agrupar_turnos(itens)
    assert [(t["falante"], t["texto"]) for t in turnos] == [
        ("cliente", "Oi tudo bem?"),
        ("atendente", "Tudo."),
        ("cliente", "Preciso de ajuda"),
    ]
    assert turnos[0]["fim"] == 4.0
    assert itens[0]["texto"] == "Oi"  # entrada original não é alterada


def test_formatar_texto_da_conversa():
    turnos = [
        {"falante": "atendente", "inicio": 0.0, "fim": 2.0, "texto": "Suporte, bom dia"},
        {"falante": "cliente", "inicio": 75.4, "fim": 80.0, "texto": "Oi"},
    ]
    assert merge.formatar(turnos) == "[00:00] Atendente: Suporte, bom dia\n[01:15] Cliente: Oi"
