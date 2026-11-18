import pytest

from app.db import STATUS_ERRO, STATUS_RECEBIDO, STATUS_TRANSCREVENDO, STATUS_TRANSCRITO, Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "t.db")


def test_criar_e_obter(db):
    i = db.criar_atendimento(inicio="2026-11-18T10:00:00", duracao_segundos=61.5, meta={"x": 1})
    a = db.obter(i)
    assert a["status"] == STATUS_RECEBIDO
    assert a["duracao_segundos"] == 61.5
    assert a["meta"] == {"x": 1}
    assert db.obter(999) is None


def test_status_e_validacao(db):
    i = db.criar_atendimento()
    db.definir_status(i, STATUS_ERRO, "falhou")
    assert db.obter(i)["erro"] == "falhou"
    db.definir_status(i, STATUS_TRANSCRITO)
    assert db.obter(i)["erro"] is None
    with pytest.raises(ValueError):
        db.definir_status(i, "inventado")


def test_segmentos_sao_substituidos_na_ordem(db):
    i = db.criar_atendimento()
    db.substituir_segmentos(i, [
        {"falante": "atendente", "inicio": 0, "fim": 1, "texto": "a"},
        {"falante": "cliente", "inicio": 1, "fim": 2, "texto": "b"},
    ])
    db.substituir_segmentos(i, [{"falante": "cliente", "inicio": 0, "fim": 1, "texto": "novo"}])
    assert [s["texto"] for s in db.listar_segmentos(i)] == ["novo"]


def test_listar_mais_recente_primeiro(db):
    a, b = db.criar_atendimento(), db.criar_atendimento()
    assert [x["id"] for x in db.listar()] == [b, a]
    assert [x["id"] for x in db.listar(limite=1)] == [b]


def test_excluir_remove_segmentos(db):
    i = db.criar_atendimento()
    db.substituir_segmentos(i, [{"falante": "cliente", "inicio": 0, "fim": 1, "texto": "x"}])
    db.excluir(i)
    assert db.obter(i) is None
    assert db.listar_segmentos(i) == []


def test_marcar_interrompidos(db):
    a = db.criar_atendimento()
    b = db.criar_atendimento()
    c = db.criar_atendimento()
    db.definir_status(b, STATUS_TRANSCREVENDO)
    db.definir_status(c, STATUS_TRANSCRITO)
    assert db.marcar_interrompidos() == 2
    assert db.obter(a)["status"] == STATUS_ERRO
    assert db.obter(b)["status"] == STATUS_ERRO
    assert db.obter(c)["status"] == STATUS_TRANSCRITO
