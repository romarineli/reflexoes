"""Provedor de embeddings PLUGÁVEL — escolhido pela env var EMBED_PROVIDER.

- `vertex`  (default): Google Vertex AI `text-multilingual-embedding-002` (768d) — GCP.
- `bedrock`: AWS Bedrock Titan `amazon.titan-embed-text-v2:0` (1024d) — AWS.
- `openai` : OpenAI `text-embedding-3-small` (1536d).

`embed_texts(texts, task)` devolve a lista de vetores alinhada à entrada.
`task`: "document" (indexação dos livros) | "query" (busca pelo tema).

Trocar de provedor = mudar EMBED_PROVIDER (+ credencial) e **re-gerar** os embeddings dos
livros, porque a dimensão/espaço vetorial muda. A dimensão vale para a coluna do pgvector.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request

PROVIDER = os.environ.get("EMBED_PROVIDER", "vertex").lower()

_DIMS = {"vertex": 768, "bedrock": 1024, "openai": 1536}


def dim() -> int:
    return int(os.environ.get("EMBED_DIM", _DIMS.get(PROVIDER, 768)))


# ---------- Vertex AI (GCP) ----------
_V_PROJECT = os.environ.get("VERTEX_PROJECT", "concrete-flight-279013")
_V_REGION = os.environ.get("VERTEX_REGION", "us-central1")
_V_MODEL = os.environ.get("VERTEX_EMBED_MODEL", "text-multilingual-embedding-002")


def _vertex_token() -> str:
    try:  # Cloud Run: metadata server
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            "service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.load(r)["access_token"]
    except Exception:  # local
        return subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()


def _vertex(texts: list[str], task: str) -> list[list[float]]:
    url = (f"https://{_V_REGION}-aiplatform.googleapis.com/v1/projects/{_V_PROJECT}"
           f"/locations/{_V_REGION}/publishers/google/models/{_V_MODEL}:predict")
    tt = "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"
    tok = _vertex_token()
    out: list[list[float]] = []
    for i in range(0, len(texts), 5):           # Vertex aceita várias instâncias por chamada
        body = json.dumps({"instances": [{"task_type": tt, "content": t}
                                          for t in texts[i:i + 5]]}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.load(r)
        out.extend(p["embeddings"]["values"] for p in d["predictions"])
    return out


# ---------- AWS Bedrock (Titan) ----------
_B_REGION = os.environ.get("AWS_REGION", "us-east-1")
_B_MODEL = os.environ.get("BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v2:0")


def _bedrock(texts: list[str], task: str) -> list[list[float]]:
    import boto3  # lazy: só quando EMBED_PROVIDER=bedrock (usa credencial AWS padrão / IAM role)
    client = boto3.client("bedrock-runtime", region_name=_B_REGION)
    out = []
    for t in texts:                              # Titan embeda 1 texto por chamada
        body = json.dumps({"inputText": t, "dimensions": dim(), "normalize": True})
        resp = client.invoke_model(modelId=_B_MODEL, body=body)
        out.append(json.loads(resp["body"].read())["embedding"])
    return out


# ---------- OpenAI ----------
_O_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def _openai(texts: list[str], task: str) -> list[list[float]]:
    body = json.dumps({"model": _O_MODEL, "input": texts}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/embeddings", data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    return [item["embedding"] for item in d["data"]]


def embed_texts(texts: list[str], task: str = "document") -> list[list[float]]:
    if PROVIDER == "vertex":
        return _vertex(texts, task)
    if PROVIDER == "bedrock":
        return _bedrock(texts, task)
    if PROVIDER == "openai":
        return _openai(texts, task)
    raise RuntimeError(f"EMBED_PROVIDER desconhecido: {PROVIDER!r} (use vertex|bedrock|openai)")
