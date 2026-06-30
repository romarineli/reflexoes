"""Carrega e resolve a config declarativa em camadas (global → app → público → botão)."""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config"


@functools.lru_cache(maxsize=None)
def _load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def matriz() -> dict:
    return _load_yaml("matriz.yaml")


def glossario() -> dict:
    return _load_yaml("glossario.yaml")


def resolve(app: str, publico: str, botao: str | None = None) -> dict:
    """Resolve a configuração efetiva de uma célula da matriz.

    Levanta ValueError se app/público/botão forem inválidos.
    """
    m = matriz()
    if app not in m["apps"]:
        raise ValueError(f"app inválido: {app!r}. Opções: {list(m['apps'])}")
    if publico not in m["publicos"]:
        raise ValueError(f"público inválido: {publico!r}. Opções: {list(m['publicos'])}")

    app_cfg = m["apps"][app]
    pub_cfg = m["publicos"][publico]

    if botao is not None:
        if botao not in pub_cfg["botoes"]:
            raise ValueError(
                f"botão {botao!r} não disponível para {publico!r}. "
                f"Disponíveis: {pub_cfg['botoes']}"
            )

    return {
        "app": app,
        "publico": publico,
        "botao": botao,
        "app_cfg": app_cfg,
        "pub_cfg": pub_cfg,
        "botao_cfg": m["botoes"].get(botao) if botao else None,
        "geracao": m["geracao"],
    }


def limite_chars(publico: str, botao: str) -> int | None:
    """Limite de caracteres efetivo de um conteúdo (None = sem limite).

    - tipos curtos (boas_vindas/push): max_chars do próprio botão.
    - reflexão (gestao_emocao): escala por público (reflexao_max_chars).
    """
    m = matriz()
    b = m["botoes"].get(botao, {}) or {}
    if b.get("max_chars"):
        return b["max_chars"]
    if botao == "gestao_emocao":
        return m["publicos"].get(publico, {}).get("reflexao_max_chars")
    return None


def religiao_para(app: str, publico: str) -> dict | None:
    """Retorna a regra de religião do glossário que casa com (app, público)."""
    for regra in glossario()["religiao"]:
        cond = regra["quando"]
        if cond.get("app") and cond["app"] != app:
            continue
        pub_cond = cond.get("publico")
        if pub_cond is not None:
            alvos = pub_cond if isinstance(pub_cond, list) else [pub_cond]
            if publico not in alvos:
                continue
        return regra
    return None
