"""Gera embeddings para os chunks do corpus, usando o provedor configurado (EMBED_PROVIDER).
Roda OFFLINE. Lê saidas/rag_corpus.jsonl e escreve saidas/rag_corpus_emb.jsonl.

  PYTHONPATH=. .venv/bin/python -m harness.rag.embed
  EMBED_PROVIDER=bedrock AWS_REGION=us-east-1 PYTHONPATH=. .venv/bin/python -m harness.rag.embed
"""
from __future__ import annotations

import json
import pathlib

from . import embeddings

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "saidas" / "rag_corpus.jsonl"
OUT = ROOT / "saidas" / "rag_corpus_emb.jsonl"
BATCH = 25


def run() -> None:
    recs = [json.loads(l) for l in CORPUS.open(encoding="utf-8")]
    print(f"Provedor: {embeddings.PROVIDER} | dimensão: {embeddings.dim()}")
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(0, len(recs), BATCH):
            batch = recs[i:i + BATCH]
            vecs = embeddings.embed_texts([r["texto"] for r in batch], task="document")
            for r, v in zip(batch, vecs):
                r["embedding"] = v
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            done = min(i + BATCH, len(recs))
            print(f"  {done}/{len(recs)} embeddings")
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    run()
