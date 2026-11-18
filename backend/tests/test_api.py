"""Testes das rotas. Exigem fastapi + httpx (pip install -r requirements.txt)."""

import dataclasses
import json
import shutil

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.transcription.fake_provider import FakeProvider  # noqa: E402

from conftest import criar_wav  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg não instalado")


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings, FakeProvider()))


def _enviar(client, tmp_path, **extra):
    mic = criar_wav(tmp_path / "up" / "microfone.wav")
    sis = criar_wav(tmp_path / "up" / "sistema.wav")
    with open(mic, "rb") as m, open(sis, "rb") as s:
        return client.post(
            "/atendimentos",
            files={"microfone": ("microfone.wav", m, "audio/wav"), "sistema": ("sistema.wav", s, "audio/wav")},
            data={"meta": json.dumps({"inicio": "2026-11-18T10:00:00"})},
            **extra,
        )


def test_health_sem_token(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_fluxo_completo(client, tmp_path):
    r = _enviar(client, tmp_path)
    assert r.status_code == 202
    i = r.json()["id"]

    detalhe = client.get(f"/atendimentos/{i}").json()
    assert detalhe["status"] == "transcrito"
    assert {t["falante"] for t in detalhe["transcricao"]} == {"atendente", "cliente"}
    assert "Atendente:" in detalhe["texto"]
    assert "pasta" not in detalhe

    assert [a["id"] for a in client.get("/atendimentos").json()] == [i]
    assert client.get(f"/atendimentos/{i}/audio/microfone").status_code == 200
    assert client.get(f"/atendimentos/{i}/audio/outro").status_code == 404

    assert client.post(f"/atendimentos/{i}/reprocessar").status_code == 202
    assert client.delete(f"/atendimentos/{i}").status_code == 204
    assert client.get(f"/atendimentos/{i}").status_code == 404


def test_extensao_invalida_nao_deixa_registro(client, tmp_path):
    r = client.post("/atendimentos", files={"microfone": ("x.exe", b"abc", "application/octet-stream")})
    assert r.status_code == 400
    assert client.get("/atendimentos").json() == []


def test_meta_invalido(client, tmp_path):
    mic = criar_wav(tmp_path / "m.wav")
    with open(mic, "rb") as m:
        r = client.post("/atendimentos", files={"microfone": ("m.wav", m)}, data={"meta": "{nao e json"})
    assert r.status_code == 400


def test_autenticacao_por_token(settings, tmp_path):
    com_token = dataclasses.replace(settings, api_token="segredo")
    c = TestClient(create_app(com_token, FakeProvider()))
    assert c.get("/atendimentos").status_code == 401
    assert c.get("/atendimentos", headers={"Authorization": "Bearer errado"}).status_code == 401
    assert c.get("/atendimentos", headers={"Authorization": "Bearer segredo"}).status_code == 200
    assert c.get("/health").status_code == 200
