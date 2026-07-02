"""Tema do dia — mapeia o dia do ano (1–365) para o framework oficial de temas
(config/temas_ano.yaml: 12 meses → 4 semanas → 5 microtemas).

Mapeamento (proposta enviada p/ aprovação da curadoria no Excel):
- Mês = mês do calendário (dia 1–31 = Janeiro, 32–59 = Fevereiro, ...).
- Dentro do mês: dias 1–7 = semana 1, 8–14 = semana 2, 15–21 = semana 3, 22–28 = semana 4.
- Dentro da semana: dias 1–5 = os 5 microtemas; dia 6 = "Integração da semana: <foco>";
  dia 7 = "Revisão da semana: <foco>".
- Dias 29–31 do mês = "Integração do mês: <tema do mês>".
Assim TODOS os 365 dias têm tema, fiel à estrutura 5-microtemas/semana do TEMA GERAL.
"""
from __future__ import annotations

import functools
import pathlib

import yaml

_CONFIG = pathlib.Path(__file__).parent / "config" / "temas_ano.yaml"
_DIAS_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # ano não-bissexto


@functools.lru_cache(maxsize=None)
def _meses() -> list[dict]:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))["meses"]


def tema_do_dia(dia: int) -> dict:
    """Tema oficial do dia (1–365). Levanta ValueError fora do intervalo."""
    if not 1 <= dia <= 365:
        raise ValueError(f"dia deve estar entre 1 e 365 (recebi {dia})")
    d = dia
    for mi, ndias in enumerate(_DIAS_MES):
        if d <= ndias:
            break
        d -= ndias
    m = _meses()[mi]
    base = {"dia": dia, "mes": m["mes"], "tema_mes": m["tema"],
            "objetivo_mes": m["objetivo"], "dia_do_mes": d}
    if d > 28:  # dias 29–31: integração do mês
        return {**base, "semana": 4, "foco": "Integração do mês",
                "tema": f"Integração do mês: {m['tema']}"}
    si = (d - 1) // 7
    s = m["semanas"][si]
    pos = (d - 1) % 7
    if pos < 5:
        tema = s["microtemas"][pos]
    elif pos == 5:
        tema = f"Integração da semana: {s['foco']}"
    else:
        tema = f"Revisão da semana: {s['foco']}"
    return {**base, "semana": si + 1, "foco": s["foco"], "tema": tema}
