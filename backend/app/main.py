"""API do Helpdesk Recorder.

Rodar (dentro da pasta backend):
    uvicorn app.main:create_app --factory --env-file .env
"""

import hmac
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from . import merge, storage
from .config import Settings, load_settings
from .db import STATUS_TRANSCREVENDO, Database
from .pipeline import processar
from .transcription import get_provider

log = logging.getLogger("api")


def create_app(settings: Optional[Settings] = None, provider=None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = settings or load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.db_path)
    provider = provider or get_provider(settings)

    interrompidos = db.marcar_interrompidos()
    if interrompidos:
        log.warning("%d atendimento(s) ficaram interrompidos; use /reprocessar", interrompidos)
    if not settings.api_token:
        log.warning("API_TOKEN vazio: API SEM autenticação. Use apenas em localhost.")

    def exigir_token(authorization: Optional[str] = Header(default=None)) -> None:
        if not settings.api_token:
            return
        esperado = f"Bearer {settings.api_token}".encode()
        recebido = (authorization or "").encode()
        if not hmac.compare_digest(recebido, esperado):
            raise HTTPException(status_code=401, detail="Token inválido ou ausente")

    auth = [Depends(exigir_token)]
    app = FastAPI(title="Helpdesk Recorder API", version="0.1.0")

    # -- helpers ---------------------------------------------------------
    def obter_ou_404(atendimento_id: int) -> dict:
        atendimento = db.obter(atendimento_id)
        if atendimento is None:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        return atendimento

    def resumo(a: dict) -> dict:
        return {
            "id": a["id"],
            "criado_em": a["criado_em"],
            "inicio": a["inicio"],
            "duracao_segundos": a["duracao_segundos"],
            "status": a["status"],
            "erro": a["erro"],
        }

    # -- rotas -----------------------------------------------------------
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/atendimentos", status_code=202, dependencies=auth)
    def criar_atendimento(
        background: BackgroundTasks,
        microfone: UploadFile = File(...),
        sistema: Optional[UploadFile] = File(default=None),
        meta: Optional[str] = Form(default=None),
    ):
        """Recebe os áudios de um atendimento e inicia a transcrição em segundo plano."""
        meta_dict: dict = {}
        if meta:
            try:
                meta_dict = json.loads(meta)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="meta deve ser JSON válido")
            if not isinstance(meta_dict, dict):
                raise HTTPException(status_code=400, detail="meta deve ser um objeto JSON")

        duracao = meta_dict.get("duracao_segundos")
        if duracao is not None and not isinstance(duracao, (int, float)):
            raise HTTPException(status_code=400, detail="meta.duracao_segundos deve ser número")

        atendimento_id = db.criar_atendimento(
            inicio=meta_dict.get("inicio"), duracao_segundos=duracao, meta=meta_dict
        )
        pasta = storage.pasta_do_atendimento(settings.data_dir, atendimento_id)
        db.definir_pasta(atendimento_id, str(pasta.relative_to(settings.data_dir)))
        max_bytes = settings.max_upload_mb * 1024 * 1024
        try:
            storage.salvar_upload(microfone.file, microfone.filename, pasta, "microfone", max_bytes)
            if sistema is not None and sistema.filename:
                storage.salvar_upload(sistema.file, sistema.filename, pasta, "sistema", max_bytes)
        except storage.UploadInvalido as e:
            db.excluir(atendimento_id)
            shutil.rmtree(pasta, ignore_errors=True)
            raise HTTPException(status_code=e.status_http, detail=str(e))

        background.add_task(processar, db, settings, provider, atendimento_id)
        return {"id": atendimento_id, "status": "recebido"}

    @app.get("/atendimentos", dependencies=auth)
    def listar_atendimentos(limite: int = 50, deslocamento: int = 0):
        limite = max(1, min(limite, 200))
        deslocamento = max(0, deslocamento)
        return [resumo(a) for a in db.listar(limite, deslocamento)]

    @app.get("/atendimentos/{atendimento_id}", dependencies=auth)
    def detalhe_atendimento(atendimento_id: int):
        atendimento = obter_ou_404(atendimento_id)
        turnos = db.listar_segmentos(atendimento_id)
        return {
            **resumo(atendimento),
            "meta": atendimento["meta"],
            "transcricao": turnos,
            "texto": merge.formatar(turnos),
        }

    @app.get("/atendimentos/{atendimento_id}/audio/{canal}", dependencies=auth)
    def baixar_audio(atendimento_id: int, canal: str):
        if canal not in storage.CANAIS:
            raise HTTPException(status_code=404, detail="Canal inexistente (microfone ou sistema)")
        atendimento = obter_ou_404(atendimento_id)
        arquivo = storage.encontrar_audio(settings.data_dir / atendimento["pasta"], canal)
        if arquivo is None:
            raise HTTPException(status_code=404, detail="Áudio não disponível para este canal")
        return FileResponse(arquivo)

    @app.post("/atendimentos/{atendimento_id}/reprocessar", status_code=202, dependencies=auth)
    def reprocessar(atendimento_id: int, background: BackgroundTasks):
        atendimento = obter_ou_404(atendimento_id)
        if atendimento["status"] == STATUS_TRANSCREVENDO:
            raise HTTPException(status_code=409, detail="Já está sendo processado")
        background.add_task(processar, db, settings, provider, atendimento_id)
        return {"id": atendimento_id, "status": "reprocessando"}

    @app.delete("/atendimentos/{atendimento_id}", status_code=204, dependencies=auth)
    def excluir_atendimento(atendimento_id: int):
        """Apaga o registro, a transcrição e os áudios (retenção/LGPD)."""
        atendimento = obter_ou_404(atendimento_id)
        if atendimento["status"] == STATUS_TRANSCREVENDO:
            raise HTTPException(status_code=409, detail="Aguarde o fim do processamento")
        if atendimento["pasta"]:
            shutil.rmtree(settings.data_dir / atendimento["pasta"], ignore_errors=True)
        db.excluir(atendimento_id)

    return app
