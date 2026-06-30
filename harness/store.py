"""Persistência — backend plugável: SQLite (dev) · PostgreSQL · MySQL/MariaDB.

Escolhido pelo esquema do DATABASE_URL:
  - postgres:// | postgresql://  → PostgreSQL (psycopg)
  - mysql://                     → MySQL/MariaDB (PyMySQL)
  - (vazio)                      → SQLite (arquivo em saidas/curadoria.db)

Guarda a curadoria (tabela `itens`) e os trechos dos livros para o RAG
(`livros_chunks`, com o embedding em texto JSON — a busca por similaridade é feita em
memória, sem precisar de pgvector/extensão).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
DB = ROOT / "saidas" / "curadoria.db"
FEWSHOT = Path(__file__).parent / "fewshot"

VEREDITOS = {"gostei", "ressalva", "nao_gostei"}

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
IS_MYSQL = DATABASE_URL.startswith("mysql://")
PH = "%s" if (IS_PG or IS_MYSQL) else "?"     # placeholder do dialeto


def _connect():
    if IS_PG:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    if IS_MYSQL:
        import pymysql
        u = urlparse(DATABASE_URL)
        return pymysql.connect(
            host=u.hostname, port=u.port or 3306, user=u.username,
            password=u.password, database=u.path.lstrip("/"),
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
    import sqlite3
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


_conn = _connect   # alias retrocompatível


def _exec(sql: str, params=(), fetch: str | None = None):
    """Executa uma query. fetch: None | 'one' | 'all' | 'lastid' | 'rowcount'.
    Linhas voltam como dict em qualquer backend."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        out = None
        if fetch == "one":
            r = cur.fetchone()
            out = dict(r) if r is not None else None
        elif fetch == "all":
            out = [dict(r) for r in cur.fetchall()]
        elif fetch == "lastid":
            out = cur.lastrowid
        elif fetch == "rowcount":
            out = cur.rowcount
        conn.commit()
        return out
    finally:
        conn.close()


# id auto-incremento por dialeto
_ID = ("BIGSERIAL PRIMARY KEY" if IS_PG else
       "BIGINT AUTO_INCREMENT PRIMARY KEY" if IS_MYSQL else
       "INTEGER PRIMARY KEY AUTOINCREMENT")


def init() -> None:
    _exec(
        f"""CREATE TABLE IF NOT EXISTS itens(
            id {_ID},
            app VARCHAR(40) NOT NULL, publico VARCHAR(40) NOT NULL, botao VARCHAR(40) NOT NULL,
            dia INTEGER, tema VARCHAR(255) NOT NULL,
            texto TEXT NOT NULL, texto_en TEXT, texto_es TEXT,
            validacao TEXT NOT NULL, ok INTEGER NOT NULL,
            veredito VARCHAR(20), comentario TEXT,
            created_at VARCHAR(32) NOT NULL, feedback_at VARCHAR(32)
        )""")
    # migração idempotente p/ tabelas que já existem sem as colunas de idioma (ex.: produção)
    for col in ("texto_en", "texto_es"):
        try:
            _exec(f"ALTER TABLE itens ADD COLUMN {col} TEXT")
        except Exception:
            pass


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def salvar_item(app: str, publico: str, botao: str, dia: int | None, tema: str,
                texto: str, validacao: dict, texto_en: str = "", texto_es: str = "") -> int:
    cols = "app,publico,botao,dia,tema,texto,texto_en,texto_es,validacao,ok,created_at"
    vals = (app, publico, botao, dia, tema, texto, texto_en, texto_es,
            json.dumps(validacao, ensure_ascii=False), int(validacao["ok"]), _now())
    ph = ",".join([PH] * 11)
    if IS_PG:   # Postgres devolve o id via RETURNING
        return _exec(f"INSERT INTO itens({cols}) VALUES({ph}) RETURNING id", vals, fetch="one")["id"]
    return _exec(f"INSERT INTO itens({cols}) VALUES({ph})", vals, fetch="lastid")


def registrar_feedback(item_id: int, veredito: str, comentario: str = "") -> None:
    if veredito not in VEREDITOS:
        raise ValueError(f"veredito inválido: {veredito!r}. Opções: {sorted(VEREDITOS)}")
    sql = f"UPDATE itens SET veredito={PH}, comentario={PH}, feedback_at={PH} WHERE id={PH}"
    n = _exec(sql, (veredito, comentario.strip(), _now(), item_id), fetch="rowcount")
    if not n:
        raise ValueError(f"item {item_id} não encontrado")


def _row(r: dict) -> dict:
    r = dict(r)
    r["validacao"] = json.loads(r["validacao"])
    return r


def listar(app: str | None = None, publico: str | None = None,
           status: str | None = None) -> list[dict]:
    """status: 'pendente' | 'avaliado' | None (todos)."""
    q = "SELECT * FROM itens WHERE 1=1"
    p: list = []
    if app:
        q += f" AND app={PH}"; p.append(app)
    if publico:
        q += f" AND publico={PH}"; p.append(publico)
    if status == "pendente":
        q += " AND veredito IS NULL"
    elif status == "avaliado":
        q += " AND veredito IS NOT NULL"
    q += " ORDER BY id DESC"
    return [_row(r) for r in _exec(q, p, fetch="all")]


def stats() -> dict:
    # SUM(CASE...) funciona em Postgres, MySQL e SQLite (FILTER não existe no MySQL)
    q = ("SELECT COUNT(*) AS total, "
         "SUM(CASE WHEN veredito IS NULL THEN 1 ELSE 0 END) AS pendentes, "
         "SUM(CASE WHEN veredito='gostei' THEN 1 ELSE 0 END) AS gostei, "
         "SUM(CASE WHEN veredito='ressalva' THEN 1 ELSE 0 END) AS ressalva, "
         "SUM(CASE WHEN veredito='nao_gostei' THEN 1 ELSE 0 END) AS nao_gostei "
         "FROM itens")
    row = _exec(q, fetch="one") or {}
    return {k: int(row.get(k) or 0) for k in ("total", "pendentes", "gostei", "ressalva", "nao_gostei")}


# ---------- RAG: trechos dos livros (embedding em texto JSON; busca em memória) ----------
def fetch_chunks(linhas: list[str]) -> list[dict]:
    """Todos os trechos das linhas pedidas (livro, texto, embedding-JSON). Vazio se a
    tabela não existir/estiver vazia (RAG inativo)."""
    if not linhas:
        return []
    marks = ",".join([PH] * len(linhas))
    try:
        return _exec(
            f"SELECT livro, texto, embedding FROM livros_chunks WHERE linha IN ({marks})",
            list(linhas), fetch="all") or []
    except Exception:
        return []


def conteudo_aprovado(app: str, publico: str, dia: int, idioma: str = "pt") -> dict:
    col = {"en": "texto_en", "es": "texto_es"}.get(idioma)
    rows = [r for r in listar(app=app, publico=publico, status="avaliado")
            if r["dia"] == dia and r["veredito"] in ("gostei", "ressalva")]
    blocos: dict[str, str] = {}
    tema = None
    for r in rows:
        if r["botao"] not in blocos:
            blocos[r["botao"]] = (r.get(col) if col else None) or r["texto"]   # fallback PT
            tema = tema or r["tema"]
    return {"tema": tema, "blocos": blocos, "idioma": idioma}


def dias_aprovados(app: str, publico: str, botoes_esperados: list[str]) -> list[dict]:
    cobertura: dict[int, set] = {}
    for r in listar(app=app, publico=publico, status="avaliado"):
        if r["veredito"] in ("gostei", "ressalva") and r["dia"] is not None:
            cobertura.setdefault(r["dia"], set()).add(r["botao"])
    esp = set(botoes_esperados)
    return [{"dia": d, "botoes": sorted(b), "completo": esp.issubset(b)}
            for d, b in sorted(cobertura.items())]


def pushes_irmaos(app: str, publico: str, tema: str, botao_atual: str) -> dict:
    out: dict[str, str] = {}
    for r in listar(app=app, publico=publico):
        b = r["botao"]
        if b.startswith("push_") and b != botao_atual and r["tema"] == tema and b not in out:
            out[b] = r["texto"]
    return out


def fewshot_curado(app: str, publico: str, botao: str | None = None, limite: int = 3) -> dict:
    avaliados = listar(app=app, publico=publico, status="avaliado")
    pos_pool = [i for i in avaliados if botao is None or i["botao"] == botao]
    positivos = [i for i in pos_pool if i["veredito"] in ("gostei", "ressalva")][:limite]
    negativos = [i for i in avaliados if i["veredito"] == "nao_gostei"][:limite]
    return {"positivos": positivos, "negativos": negativos}


def exportar_fewshot() -> dict:
    avaliados = listar(status="avaliado")
    aprovados = [i for i in avaliados if i["veredito"] in ("gostei", "ressalva")]
    reprovados = [i for i in avaliados if i["veredito"] == "nao_gostei"]

    def bloco(i: dict) -> str:
        cab = f"## {i['app'].upper()} · {i['publico'].upper()} · {i['botao']}"
        if i["dia"]:
            cab += f" · Dia {i['dia']}"
        cab += f" — {i['tema']}"
        partes = [cab, "", i["texto"]]
        if i["comentario"]:
            tag = "Ressalva da curadoria" if i["veredito"] == "ressalva" else "Comentário"
            partes += ["", f"> **{tag}:** {i['comentario']}"]
        return "\n".join(partes)

    pos = "# Few-shot CURADO — aprovados pela curadoria\n\n" + "\n\n---\n\n".join(map(bloco, aprovados))
    neg = "# Few-shot CURADO — reprovados pela curadoria\n\n" + "\n\n---\n\n".join(map(bloco, reprovados))
    try:
        (FEWSHOT / "curados_positivos.md").write_text(pos, encoding="utf-8")
        (FEWSHOT / "curados_negativos.md").write_text(neg, encoding="utf-8")
    except Exception:
        pass
    markdown = (f"# Few-shot curado — {len(aprovados)} aprovados · {len(reprovados)} reprovados\n\n"
                f"{pos}\n\n\n{neg}")
    return {"aprovados": len(aprovados), "reprovados": len(reprovados), "markdown": markdown}
