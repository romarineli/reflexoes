"""Ingestão dos livros para o RAG: extrai texto dos PDFs, limpa e chunka com metadados.

Saída: saidas/rag_corpus.jsonl (uma linha por chunk). Próximo passo: embeddings + pgvector.
Roda OFFLINE (não faz parte do container de serving).

  PYTHONPATH=. .venv/bin/python -m harness.rag.ingest
"""
from __future__ import annotations

import json
import pathlib
import re

import fitz  # pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVROS = ROOT / "material" / "Livros Augusto Cury"
OUT = ROOT / "saidas" / "rag_corpus.jsonl"

ALVO = 3500      # ~caracteres por chunk (~800 tokens)
OVERLAP = 400    # sobreposição entre chunks p/ não cortar contexto


def _limpa(t: str) -> str:
    t = t.replace("\r", "\n")
    t = re.sub(r"-\n(\w)", r"\1", t)        # junta hifenização de quebra de linha
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n\n", t)
    return t.strip()


def _chunks(texto: str):
    """Janela deslizante por caracteres, cortando preferencialmente em fim de frase.

    Robusto a livros sem quebras de parágrafo (a extração de PDF costuma perdê-las).
    """
    n = len(texto)
    i = 0
    while i < n:
        end = min(i + ALVO, n)
        if end < n:  # tenta ajustar o corte para um fim de frase próximo
            janela = texto[i:end]
            corte = max(janela.rfind(". "), janela.rfind(".\n"),
                        janela.rfind("! "), janela.rfind("? "))
            if corte > ALVO * 0.5:
                end = i + corte + 1
        trecho = texto[i:end].strip()
        if trecho:
            yield trecho
        if end >= n:
            break
        i = max(end - OVERLAP, i + 1)         # garante progresso + overlap


def run() -> None:
    OUT.parent.mkdir(exist_ok=True)
    total = 0
    by_book: dict[str, int] = {}
    with OUT.open("w", encoding="utf-8") as f:
        for linha in ["Geral", "Cristo"]:
            for pdf in sorted((LIVROS / linha).glob("*.pdf")):
                doc = fitz.open(pdf)
                texto = _limpa("".join(p.get_text() for p in doc))
                doc.close()
                c = 0
                for idx, ch in enumerate(_chunks(texto)):
                    rec = {
                        "id": f"{linha}/{pdf.stem}#{idx}",
                        "linha": linha.lower(),   # geral | cristo
                        "livro": pdf.stem,
                        "chunk": idx,
                        "texto": ch,
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    c += 1
                    total += 1
                by_book[pdf.name] = c
    for k, v in by_book.items():
        print(f"  {v:>4} chunks  {k[:52]}")
    print(f"\ntotal: {total} chunks -> {OUT}")


if __name__ == "__main__":
    run()
