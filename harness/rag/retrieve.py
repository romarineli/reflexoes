"""Recuperação RAG por busca em memória (sem pgvector).

Embeda o tema (provedor plugável) e calcula a similaridade de cosseno contra os ~987
trechos dos livros, carregados do banco uma vez por processo (cache). Funciona em qualquer
banco (SQLite/Postgres/MySQL), já que a similaridade é feita na aplicação.

Se a tabela de trechos estiver vazia/ausente, devolve [] (RAG inativo, sem quebrar).
"""
from __future__ import annotations

import json

from .. import store
from . import embeddings

# de qual linha de livros cada app pode beber
LINHAS = {"lifecalm": ["cristo", "geral"], "spotcalm": ["geral"]}

_CACHE: dict[tuple, tuple] = {}   # chave: linhas → (meta, matriz normalizada)


def _carregar(linhas: list[str]):
    chave = tuple(sorted(linhas))
    if chave in _CACHE:
        return _CACHE[chave]
    import numpy as np
    rows = store.fetch_chunks(linhas)
    meta = [{"livro": r["livro"], "texto": r["texto"]} for r in rows]
    if rows:
        mat = np.array([json.loads(r["embedding"]) for r in rows], dtype="float32")
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        mat = mat / norms                       # normaliza p/ cosseno = produto interno
    else:
        mat = None
    _CACHE[chave] = (meta, mat)
    return _CACHE[chave]


def buscar(app: str, tema: str, k: int = 3) -> list[dict]:
    """Top-k trechos dos livros mais próximos do tema, filtrando pela linha do app."""
    linhas = LINHAS.get(app, ["geral", "cristo"])
    meta, mat = _carregar(linhas)
    if not meta:
        return []
    import numpy as np
    q = np.array(embeddings.embed_texts([tema], task="query")[0], dtype="float32")
    q = q / (np.linalg.norm(q) or 1.0)
    sims = mat @ q
    idx = np.argsort(-sims)[:k]
    return [meta[i] for i in idx]
