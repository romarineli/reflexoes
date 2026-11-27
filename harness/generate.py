"""Geração validada — usada pela API e pelo CLI.

Monta o prompt, gera no Claude e regenera quando a saída quebra uma regra dura:
limite de caracteres (frase do dia, push) ou repetição do molde de pergunta de um dia
recente. Centraliza a lógica num só lugar.
"""
from __future__ import annotations

from . import client, config, prompt, store, translate, validate

JANELA_REPETICAO = 30   # dias anteriores considerados ao checar repetição de pergunta


def _perguntas_recentes(app: str, publico: str, botao: str, dia: int | None) -> list[str]:
    """Perguntas já usadas nos dias anteriores — vazio se não há dia ou banco."""
    if not dia:
        return []
    try:
        textos = store.textos_recentes(app, publico, botao, dia, JANELA_REPETICAO)
    except Exception as e:  # banco indisponível não pode derrubar a geração
        print(f"[repetição] histórico indisponível: {e}", flush=True)
        return []
    return [q for t in textos for q in validate.perguntas(t)]


def gerar(app: str, publico: str, botao: str, tema: str,
          dia: int | None = None, tentativas_limite: int = 3,
          evitar_perguntas: list[str] | None = None) -> dict:
    # Cada dia é gerado isolado, então o modelo não sabe o que escreveu nos dias vizinhos
    # e cai no mesmo molde ("Quando foi a última vez que você..."). O histórico entra no
    # prompt como o que NÃO repetir, e o que escapar disso é barrado abaixo.
    evitar = (evitar_perguntas if evitar_perguntas is not None
              else _perguntas_recentes(app, publico, botao, dia))

    system = prompt.build_system(app, publico, botao, tema,   # valida app/público/botão
                                 evitar_perguntas=evitar)
    user = prompt.build_user(app, publico, botao, tema, dia)
    texto = client.generate(system, user)

    lim = config.limite_chars(publico, botao)
    for _ in range(tentativas_limite):
        reforco = []
        if lim and len(texto) > lim:
            reforco.append(f"O texto anterior tinha {len(texto)} caracteres e ESTOUROU o "
                           f"limite. Reescreva com NO MÁXIMO {lim} caracteres, mantendo o "
                           "sentido e o tom.")
        repetidos = validate.repeticoes(texto, evitar)
        if repetidos:
            moldes = ", ".join(f'"{m}..."' for m in repetidos)
            reforco.append(f"As perguntas do texto anterior abriam como as de um dia recente "
                           f"({moldes}). Reescreva começando as perguntas de outra forma — "
                           "outro ângulo, não a mesma abertura com outras palavras.")
        if not reforco:
            break
        texto = client.generate(system, user + "\n\n" + "\n\n".join(reforco))

    val = validate.report(texto, app, publico, botao, anteriores=evitar)
    traducoes = translate.traduzir_todos(texto)   # {'en': ..., 'es': ...} (fiel ao PT)
    return {"app": app, "publico": publico, "botao": botao, "dia": dia,
            "tema": tema, "texto": texto, "traducoes": traducoes, "validacao": val}
