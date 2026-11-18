import json

from configuracao import carregar_config


def test_padroes_quando_nao_ha_arquivos(tmp_path):
    cfg = carregar_config(tmp_path)
    assert cfg["backend_url"] == "http://localhost:8000"
    assert cfg["pasta_saida"] == tmp_path / "atendimentos"


def test_local_sobrescreve_config_e_env_sobrescreve_tudo(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"backend_url": "http://a:1", "api_token": ""}))
    (tmp_path / "config.local.json").write_text(json.dumps({"api_token": "do-arquivo"}))
    monkeypatch.delenv("HELPDESK_API_TOKEN", raising=False)
    cfg = carregar_config(tmp_path)
    assert cfg["backend_url"] == "http://a:1" and cfg["api_token"] == "do-arquivo"

    monkeypatch.setenv("HELPDESK_API_TOKEN", "do-ambiente")
    assert carregar_config(tmp_path)["api_token"] == "do-ambiente"


def test_pasta_absoluta_e_mantida(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"pasta_saida": str(tmp_path / "fora")}))
    assert carregar_config(tmp_path)["pasta_saida"] == tmp_path / "fora"
