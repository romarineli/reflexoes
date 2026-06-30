"""API de curadoria (FastAPI). Serve o front e expõe geração + feedback.

Rodar:
  PYTHONPATH=. .venv/bin/uvicorn harness.api:app --reload --port 8000
Depois abrir http://localhost:8000
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import config, generate, store

WEBUI = Path(__file__).parent / "webui"

app = FastAPI(title="Curadoria — Textos Reflexivos")

# Proteção opcional por HTTP Basic. Ativa só se BASIC_AUTH_USER e BASIC_AUTH_PASS
# estiverem no ambiente (homolog). Em dev local, sem essas vars, fica desligada.
_AUTH_USER = os.environ.get("BASIC_AUTH_USER")
_AUTH_PASS = os.environ.get("BASIC_AUTH_PASS")
_CONTENT_KEY = os.environ.get("CONTENT_API_KEY")   # auth máquina-a-máquina p/ /content/*


@app.middleware("http")
async def _auth(request: Request, call_next):
    path = request.url.path
    # Health check do ECS/ALB
    if path == "/health":
        return await call_next(request)
    # API de entrega (consumida pelo backend do app): autentica por X-API-Key
    if path.startswith("/content/"):
        if _CONTENT_KEY and not secrets.compare_digest(
                request.headers.get("x-api-key", ""), _CONTENT_KEY):
            return Response(status_code=401, content="x-api-key inválida")
        return await call_next(request)
    # Demais rotas (UI/curadoria): HTTP Basic
    if _AUTH_USER and _AUTH_PASS:
        import base64
        head = request.headers.get("authorization", "")
        ok = False
        if head.startswith("Basic "):
            try:
                user, _, pwd = base64.b64decode(head[6:]).decode().partition(":")
                ok = (secrets.compare_digest(user, _AUTH_USER)
                      and secrets.compare_digest(pwd, _AUTH_PASS))
            except Exception:
                ok = False
        if not ok:
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return await call_next(request)


@app.on_event("startup")
def _startup() -> None:
    store.init()


# ---------- modelos de request ----------
class GerarReq(BaseModel):
    app: str
    publico: str
    botao: str = "gestao_emocao"
    tema: str
    dia: int | None = None


class GerarDiaReq(BaseModel):
    app: str
    publico: str
    tema: str
    dia: int | None = None


class FeedbackReq(BaseModel):
    veredito: str          # gostei | ressalva | nao_gostei
    comentario: str = ""


# ---------- config para os dropdowns ----------
@app.get("/api/config")
def get_config() -> dict:
    m = config.matriz()
    return {
        "apps": {k: v["nome"] for k, v in m["apps"].items()},
        "publicos": {k: {"rotulo": v["rotulo"], "botoes": v["botoes"]} for k, v in m["publicos"].items()},
        "botoes": {k: v["rotulo"] for k, v in m["botoes"].items()},
        "temas_sugeridos": [
            "A importância da calma", "Aprender a ouvir", "Respeitar os próprios limites",
            "A força da gentileza", "Aprender a esperar", "A importância de pedir desculpas",
            "Aprender a agradecer as pessoas", "Aprender a confiar mais em si mesmo",
            "A importância de ajudar as pessoas", "Cuidar da própria mente",
        ],
    }


def _gerar_e_salvar(app_: str, publico: str, botao: str, tema: str, dia: int | None) -> dict:
    try:
        r = generate.gerar(app_, publico, botao, tema, dia)
    except ValueError as e:
        raise HTTPException(400, str(e))
    r["id"] = store.salvar_item(app_, publico, botao, dia, tema, r["texto"], r["validacao"])
    r["veredito"] = None
    return r


@app.post("/api/gerar")
def gerar(req: GerarReq) -> dict:
    return _gerar_e_salvar(req.app, req.publico, req.botao, req.tema, req.dia)


@app.post("/api/gerar-dia")
def gerar_dia(req: GerarDiaReq) -> list[dict]:
    """Gera todos os botões do público (dia completo)."""
    try:
        cfg = config.resolve(req.app, req.publico)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return [_gerar_e_salvar(req.app, req.publico, b, req.tema, req.dia)
            for b in cfg["pub_cfg"]["botoes"]]


@app.get("/api/itens")
def itens(app: str | None = None, publico: str | None = None, status: str | None = None) -> dict:
    return {"itens": store.listar(app, publico, status), "stats": store.stats()}


@app.post("/api/itens/{item_id}/feedback")
def feedback(item_id: int, req: FeedbackReq) -> dict:
    try:
        store.registrar_feedback(item_id, req.veredito, req.comentario)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/exportar-fewshot")
def exportar() -> dict:
    return store.exportar_fewshot()


# ---------- API de entrega (consumida pelo backend do app) ----------
@app.get("/content/daily")
def content_daily(app: str, publico: str, dia: int) -> dict:
    """Conteúdo aprovado do dia para um perfil. As regras de horário/quantidade/perfil
    ficam no app; aqui só entregamos o que a curadoria validou."""
    try:
        config.resolve(app, publico)
    except ValueError as e:
        raise HTTPException(400, str(e))
    data = store.conteudo_aprovado(app, publico, dia)
    if not data["blocos"]:
        raise HTTPException(404, "sem conteúdo aprovado para este perfil/dia")
    return {"app": app, "publico": publico, "dia": dia,
            "tema": data["tema"], "blocos": data["blocos"]}


@app.get("/content/status")
def content_status(app: str, publico: str) -> dict:
    """Cobertura: quais dias já têm conteúdo aprovado e quais estão completos."""
    try:
        cfg = config.resolve(app, publico)
    except ValueError as e:
        raise HTTPException(400, str(e))
    dias = store.dias_aprovados(app, publico, cfg["pub_cfg"]["botoes"])
    return {"app": app, "publico": publico,
            "completos": sum(1 for d in dias if d["completo"]), "dias": dias}


# ---------- front ----------
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEBUI / "index.html")
