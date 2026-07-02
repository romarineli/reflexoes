"""Cliente do provider (Anthropic / Claude). Carrega a chave do .env."""
from __future__ import annotations

import os
from pathlib import Path

from . import config

_ROOT = Path(__file__).parent.parent


def _load_env() -> None:
    """Carrega .env simples (KEY=VALUE) para o ambiente, se ainda não setado."""
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def generate(system: str, user: str, *, modelo: str | None = None,
             temperatura: float | None = None, max_tokens: int = 1500) -> str:
    """Gera um texto. Levanta erro claro se a chave/lib faltarem."""
    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY não encontrada (.env ou ambiente).")
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Pacote 'anthropic' não instalado. pip install anthropic") from e

    g = config.matriz()["geracao"]
    kwargs = dict(
        model=modelo or g["modelo"],
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # temperature é deprecado em alguns modelos (ex.: Opus 4.8). Só envia se definido.
    temp = temperatura if temperatura is not None else g.get("temperatura")
    if temp is not None:
        kwargs["temperature"] = temp

    client = anthropic.Anthropic()
    # Retry em erros TRANSITÓRIOS (sobrecarga/limite/timeout) — evita "Falha ao gerar" à toa.
    import time
    erro = None
    for tentativa in range(4):
        try:
            msg = client.messages.create(**kwargs)
            return "".join(b.text for b in msg.content if b.type == "text").strip()
        except Exception as e:  # noqa: BLE001
            erro = e
            s = str(e).lower()
            transitorio = any(t in s for t in (
                "overloaded", "rate limit", "429", "529", "503", "500",
                "timeout", "timed out", "connection", "temporarily"))
            if not transitorio or tentativa == 3:
                raise
            time.sleep(1.5 * (tentativa + 1))   # backoff: 1.5s, 3s, 4.5s
    raise erro
