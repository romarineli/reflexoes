"""Carrega os chunks+embeddings no banco (qualquer um: SQLite/Postgres/MySQL).

O embedding vai como TEXTO JSON (a busca por similaridade é feita em memória — ver
retrieve.py). Sem pgvector/extensão. Roda OFFLINE; usa o DATABASE_URL do ambiente
(vazio = SQLite local).

  PYTHONPATH=. .venv/bin/python -m harness.rag.load_db
  DATABASE_URL=mysql://user:pass@host/db PYTHONPATH=. .venv/bin/python -m harness.rag.load_db
"""
from __future__ import annotations

import json
import pathlib

from .. import store

ROOT = pathlib.Path(__file__).resolve().parents[2]
EMB = ROOT / "saidas" / "rag_corpus_emb.jsonl"

# tipo de coluna de texto grande por dialeto
_BIGTEXT = "LONGTEXT" if store.IS_MYSQL else "TEXT"


def run() -> None:
    recs = [json.loads(l) for l in EMB.open(encoding="utf-8")]
    store._exec("DROP TABLE IF EXISTS livros_chunks")
    store._exec(
        f"""CREATE TABLE livros_chunks(
            id VARCHAR(255) PRIMARY KEY, linha VARCHAR(20), livro VARCHAR(255),
            chunk INTEGER, texto TEXT, embedding {_BIGTEXT})""")
    ph = ",".join([store.PH] * 6)
    conn = store._connect()
    try:
        cur = conn.cursor()
        cur.executemany(
            f"INSERT INTO livros_chunks(id,linha,livro,chunk,texto,embedding) VALUES({ph})",
            [(r["id"], r["linha"], r["livro"], r["chunk"], r["texto"],
              json.dumps(r["embedding"])) for r in recs])
        conn.commit()
    finally:
        conn.close()
    n = store._exec("SELECT COUNT(*) AS n FROM livros_chunks", fetch="one")["n"]
    print(f"linhas carregadas: {n} (backend: {'mysql' if store.IS_MYSQL else 'postgres' if store.IS_PG else 'sqlite'})")


if __name__ == "__main__":
    run()
