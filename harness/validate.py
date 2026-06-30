"""Validação automática — camada de regras DURAS (determinística, custo zero).

v1: detecta violações de vocabulário do glossario.yaml. O juiz LLM de tom (Fase 2)
entra depois. Retorna lista de violações; vazio = passou.
"""
from __future__ import annotations

import re
import unicodedata

from . import config


def _norm(s: str) -> str:
    """Minúsculas + sem acentos, para casar termos de forma robusta."""
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# Detector de diminutivos por padrão (-inho/-inha/-zinho/-zinha).
# Exige radical de 3+ letras → já exclui "minha/tinha/vinha/linha/rainha/ninho/pinho/vinho".
_DIM_RE = re.compile(r"\b[a-z]{3,}(?:zinh|inh)[oa]s?\b")
# Palavras legítimas que casam o padrão mas NÃO são diminutivos (normalizadas, sem acento).
_DIM_OK = {
    "caminho", "carinho", "sozinho", "sozinha", "vizinho", "vizinha", "vizinhos", "vizinhas",
    "padrinho", "madrinha", "sobrinho", "sobrinha", "sobrinhos", "sobrinhas",
    "golfinho", "golfinhos", "focinho", "espinho", "espinhos", "espinha", "espinhas",
    "marinho", "marinha", "galinha", "galinhas", "farinha", "cozinha", "cozinhas",
    "sardinha", "ladainha", "campainha", "rainha", "andorinha", "andorinhas", "moinho",
    # formas verbais (imperfeito de ter/vir e derivados)
    "continha", "continham", "mantinha", "mantinham", "obtinha", "detinha", "retinha",
    "convinha", "provinha", "advinha", "adivinha", "sustinha", "intervinha",
}


def _contains(texto_norm: str, termo: str) -> bool:
    # Fronteira de palavra só no INÍCIO; o fim fica livre para capturar flexões
    # do português (plural/conjugação): "inteligente" casa "inteligentes",
    # "corpinho" casa "corpinhos". Prefere super-detectar (e regenerar) a deixar passar.
    t = re.escape(_norm(termo))
    return re.search(rf"(?<![a-z]){t}", texto_norm) is not None


def check(texto: str, app: str, publico: str, botao: str | None = None) -> list[str]:
    g = config.glossario()
    tn = _norm(texto)
    viol: list[str] = []

    # 0) Limite de caracteres (tipos curtos e reflexão por público)
    if botao:
        lim = config.limite_chars(publico, botao)
        if lim and len(texto) > lim:
            viol.append(f"excede o limite de caracteres: {len(texto)}/{lim}")

    # 1) Proibidos globais
    for item in g["proibidos_globais"]:
        if _contains(tn, item["termo"]):
            usar = ", ".join(item.get("usar", [])) or "(ver regras)"
            viol.append(f'termo proibido "{item["termo"]}" → usar: {usar}')

    # 2) Religião condicional
    regra = config.religiao_para(app, publico)
    if regra:
        for termo in regra.get("proibidos", []):
            if _contains(tn, termo):
                viol.append(f'religião: termo proibido para {app}/{publico}: "{termo}"')

    # 3) Diminutivos (só públicos restritos) — lista explícita + padrão -inho/-inha/-zinho
    dim = g["diminutivos"]
    if publico in dim["proibido_para"]:
        achados = set()
        for termo in dim["exemplos_proibidos"]:
            if _contains(tn, termo):
                achados.add(_norm(termo))
        for m in _DIM_RE.finditer(tn):
            w = m.group(0)
            if w not in _DIM_OK:
                achados.add(w)
        for w in sorted(achados):
            viol.append(f'diminutivo não permitido para {publico}: "{w}"')

    return viol


def report(texto: str, app: str, publico: str, botao: str | None = None) -> dict:
    v = check(texto, app, publico, botao)
    return {"ok": not v, "violacoes": v}
