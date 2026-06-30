"""Geração validada — usada pela API e pelo CLI.

Monta o prompt, gera no Claude e, para tipos com limite de caracteres (frase do dia,
push), regenera se a saída estourar o limite. Centraliza a lógica num só lugar.
"""
from __future__ import annotations

from . import client, config, prompt, validate


def gerar(app: str, publico: str, botao: str, tema: str,
          dia: int | None = None, tentativas_limite: int = 3) -> dict:
    system = prompt.build_system(app, publico, botao, tema)   # valida app/público/botão
    user = prompt.build_user(app, publico, botao, tema, dia)
    texto = client.generate(system, user)

    lim = config.limite_chars(publico, botao)
    n = 0
    while lim and len(texto) > lim and n < tentativas_limite:
        n += 1
        reforco = (user + f"\n\nO texto anterior tinha {len(texto)} caracteres e ESTOUROU o "
                   f"limite. Reescreva com NO MÁXIMO {lim} caracteres, mantendo o sentido e o tom.")
        texto = client.generate(system, reforco)

    val = validate.report(texto, app, publico, botao)
    return {"app": app, "publico": publico, "botao": botao, "dia": dia,
            "tema": tema, "texto": texto, "validacao": val}
