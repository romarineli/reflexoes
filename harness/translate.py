"""Tradução dos textos (PT → EN/ES). O PT é o canônico/curado; aqui só traduzimos fiel.

Usa um modelo rápido/barato (config `geracao.modelo_traducao`). Preserva tom, estrutura
(parágrafos + pergunta final), comprimento aproximado e as figuras (Mestre dos Mestres,
Jesus Cristo). Resiliente: em erro, devolve "".
"""
from __future__ import annotations

from . import client, config

# idiomas não-PT entregues pelo sistema
NAO_PT = [i for i in config.matriz().get("geracao", {}).get("idiomas", ["pt"]) if i != "pt"]

_ALVO = {
    "en": "inglês (English)",
    "es": "espanhol (Español)",
    "fr": "francês (Français)",
    "it": "italiano (Italiano)",
}


def traduzir(texto: str, idioma: str) -> str:
    alvo = _ALVO.get(idioma)
    if not texto or not texto.strip() or not alvo:
        return ""
    system = (
        "Você é tradutor especializado em textos reflexivos de bem-estar emocional. "
        f"Traduza o texto para {alvo}, de forma NATURAL e nativa (não literal), preservando: "
        "o tom acolhedor, reflexivo e humano; a estrutura (mesmos parágrafos e a pergunta final, "
        "se houver); e o comprimento aproximado. "
        "Mantenha as figuras: 'o Mestre dos Mestres' → 'the Master of Masters' / 'el Maestro de "
        "los Maestros'; 'Jesus Cristo' → 'Jesus Christ' / 'Jesucristo'. "
        "NÃO acrescente nem remova ideias. Responda APENAS com a tradução, sem comentários."
    )
    modelo = config.matriz().get("geracao", {}).get("modelo_traducao")
    try:
        return client.generate(system, texto, modelo=modelo)
    except Exception:
        return ""


def traduzir_todos(texto: str) -> dict:
    """{'en': ..., 'es': ...} para todos os idiomas não-PT configurados."""
    return {idi: traduzir(texto, idi) for idi in NAO_PT}
