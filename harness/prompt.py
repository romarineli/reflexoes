"""Monta o system prompt e a mensagem de geração a partir da config resolvida."""
from __future__ import annotations

import re
from pathlib import Path

from . import config, store
from .rag import retrieve

BASE = Path(__file__).parent
TEMPLATE = (BASE / "prompts" / "system_base.md").read_text(encoding="utf-8")
FEWSHOT_POS = (BASE / "fewshot" / "positivos.md").read_text(encoding="utf-8")
FEWSHOT_NEG = (BASE / "fewshot" / "negativos.md").read_text(encoding="utf-8")


def _fmt_curado(i: dict) -> str:
    cab = f"{i['app'].upper()} · {i['publico'].upper()} · {i['botao']}"
    if i.get("dia"):
        cab += f" · Dia {i['dia']}"
    cab += f" — {i['tema']}"
    txt = f"**{cab}**\n{i['texto']}"
    if i.get("comentario"):
        txt += f"\n> Curadoria: {i['comentario']}"
    return txt


def _rag_trechos(app: str, tema: str) -> str:
    """Trechos dos livros recuperados por similaridade, como fundamento (não literal)."""
    try:
        trechos = retrieve.buscar(app, tema)
    except Exception as e:  # resiliente + observável nos logs
        print(f"[RAG] erro, gerando sem fundamento: {e}", flush=True)
        return ""
    print(f"[RAG] {len(trechos)} trecho(s) | app={app} | tema={tema!r}", flush=True)
    if not trechos:
        return ""
    blocos = "\n\n".join(f"— De *{t['livro']}*:\n{t['texto'][:1200].strip()}" for t in trechos)
    return ("## Fundamento na obra de Augusto Cury\n"
            "Use os trechos abaixo como **base conceitual e de essência** — capte as ideias, "
            "NÃO copie frases literais:\n\n" + blocos)


def _fewshot_dinamico(app: str, publico: str, botao: str) -> tuple[str, str]:
    """Anexa aos exemplos fixos os exemplos recém-curados pela Letícia (do banco).

    Resiliente: qualquer falha no banco devolve só os exemplos fixos.
    """
    pos, neg = FEWSHOT_POS, FEWSHOT_NEG
    try:
        cur = store.fewshot_curado(app, publico, botao)
    except Exception:
        return pos, neg
    if cur["positivos"]:
        pos += ("\n\n---\n\n### Recém-APROVADOS pela curadoria — siga estes de perto\n\n"
                + "\n\n".join(_fmt_curado(i) for i in cur["positivos"]))
    if cur["negativos"]:
        neg += ("\n\n---\n\n### Recém-REPROVADOS pela curadoria — NÃO repita estes\n\n"
                + "\n\n".join(_fmt_curado(i) for i in cur["negativos"]))
    return pos, neg


def _perfil_publico(pub_cfg: dict) -> str:
    linhas = [f"- Profundidade do texto: **{pub_cfg.get('profundidade', 'media')}**."]
    if pub_cfg.get("universo"):
        linhas.append("- Ancorar no universo real do público: " + ", ".join(pub_cfg["universo"]) + ".")
    if pub_cfg.get("cotidiano"):
        linhas.append("- Cotidiano do público: " + ", ".join(pub_cfg["cotidiano"]) + ".")
    if pub_cfg.get("exercicios_preferidos"):
        linhas.append("- Exercícios preferidos (variar entre os dias): " + ", ".join(pub_cfg["exercicios_preferidos"]) + ".")
    if pub_cfg.get("nota"):
        linhas.append(f"- Atenção: {pub_cfg['nota'].strip()}")
    return "\n".join(linhas)


def _bloco_religiao(app: str, publico: str) -> str:
    regra = config.religiao_para(app, publico)
    if not regra:
        return ""
    if regra.get("proibidos"):
        proib = ", ".join(f'"{t}"' for t in regra["proibidos"])
        if regra.get("usar"):
            usar = ", ".join(f'"{t}"' for t in regra["usar"])
            return f"- RELIGIÃO: NUNCA use {proib}. Use no lugar: {usar}."
        return f"- RELIGIÃO: NUNCA use {proib}. {regra.get('nota', '')}".strip()
    if regra.get("permitido"):
        perm = ", ".join(f'"{t}"' for t in regra["permitido"])
        extra = " Não use as perífrases da versão adulta." if regra.get("evitar_periphrase_adulta") else ""
        return f"- RELIGIÃO: para este público, use SOMENTE {perm} como referência cristã.{extra}"
    return ""


# Parágrafos sugeridos por profundidade do público (reflexão da Gestão da Emoção)
_PARAGRAFOS = {"alta": "3 a 4 parágrafos", "media": "2 a 3 parágrafos", "baixa": "2 a 3 frases simples e visuais"}


def _formato_botao(botao: str, app: str, publico: str, pub_cfg: dict, botao_cfg: dict | None) -> str:
    rotulo = (botao_cfg or {}).get("rotulo", botao)
    prof = pub_cfg.get("profundidade", "media")
    is_kids = "historia" in pub_cfg["botoes"]

    # Tipos CURTOS com limite de caracteres
    lim = (botao_cfg or {}).get("max_chars")
    if botao == "boas_vindas":
        return (f"**{rotulo}** — Gere UMA única frase curta para a tela inicial: de impacto, "
                f"acolhedora, reflexiva e humanizada. **No máximo {lim} caracteres.** "
                "Sem aspas, sem emojis, sem pergunta. Apenas a frase.")
    if botao.startswith("push_"):
        periodo = (botao_cfg or {}).get("periodo", "")
        return (f"**{rotulo}** — Gere o texto de UMA notificação push para o período da "
                f"**{periodo}**, conectada ao tema do dia: curta, acolhedora e que convide a "
                f"abrir o app. **No máximo {lim} caracteres** (precisa caber na notificação). "
                "Uma frase, sem aspas, sem emojis. Apenas o texto da notificação.")

    if botao == "gestao_emocao":
        lim = pub_cfg.get("reflexao_max_chars")
        limtxt = (f" O texto inteiro deve ter NO MÁXIMO {lim} caracteres." if lim else "")
        return (
            f"**{rotulo}** — Gere SOMENTE a reflexão central do dia: {_PARAGRAFOS.get(prof)}, "
            "**parágrafos curtos (2 a 3 frases cada)**, terminando OBRIGATORIAMENTE com UMA "
            f"pergunta provocativa na última linha.{limtxt}\n"
            "NÃO inclua exercício prático, passo a passo, 'Exercício de hoje', técnica de "
            "respiração nem desafio — isso pertence a outros botões."
        )

    if botao == "exercicio_antiestresse":
        if is_kids:
            return (
                f"**{rotulo}** (Kids) — Gere SOMENTE a prática, no formato:\n"
                "Querida família, [prática lúdica com um nome].\n"
                'Como aplicar: "[instrução em fala direta para a criança]".\n'
                "Por que funciona: [benefício emocional em 1 linha].\n"
                "Pergunta de reflexão: [uma pergunta curta para a família/criança, ligada à prática].\n"
                "NÃO inclua a reflexão da Gestão da Emoção."
            )
        return (
            f"**{rotulo}** — Gere a prática aplicável do dia: UMA prática concreta e curta "
            "(no MÁXIMO duas opções — NÃO liste três ou mais). "
            "FINALIZE com uma breve pergunta de reflexão ligada a esta prática.\n"
            "NÃO reescreva a reflexão da Gestão da Emoção."
        )

    if botao == "calma_noturna":
        if is_kids:
            return (
                f"**{rotulo}** (Kids) — Gere TRÊS blocos, nesta ordem e rotulados:\n"
                "1) Calma Noturna: 1–2 frases sensoriais de relaxamento (sem diminutivos);\n"
                "2) HISTÓRIA: narrativa curta (4–7 frases) com personagem de nome bíblico "
                "(Lucas, Samuel, Maria, Davi, Pedro…), no cotidiano infantil ligado ao tema, "
                "com uma lição ao final;\n"
                "3) Desafio: uma ação concreta e executável ligada ao tema, terminando com uma "
                "pergunta de reflexão associada ao desafio."
            )
        extra = ""
        if app == "lifecalm" and publico == "adultos":
            extra = (" Traga com naturalidade uma referência ao Mestre dos Mestres (ou 'o mestre "
                     "do amor' / 'o Homem mais Inteligente da História') como modelo de serenidade.")
        return (
            f"**{rotulo}** — Gere SOMENTE 1 a 2 frases de fechamento do dia, acolhedoras e "
            f"ritualísticas, reforçando o tema.{extra} Sem exercício e sem pergunta provocativa."
        )

    if botao == "desafio":
        return (f"**{rotulo}** — Gere uma ação concreta e executável ligada ao tema do dia e "
                "FINALIZE com uma pergunta de reflexão associada ao desafio.")

    # fallback (historia gerada isoladamente, se pedida)
    return f"**{rotulo}** — {(botao_cfg or {}).get('descricao', '')}"


def build_system(app: str, publico: str, botao: str, tema: str) -> str:
    r = config.resolve(app, publico, botao)
    app_cfg, pub_cfg = r["app_cfg"], r["pub_cfg"]

    regra_dim = ""
    if app and publico in config.glossario()["diminutivos"]["proibido_para"]:
        regra_dim = ("- NUNCA use diminutivos (corpinho, mãozinha, olhinhos, etc.) — "
                     "este público não permite.")

    fewshot_pos, fewshot_neg = _fewshot_dinamico(app, publico, botao)

    formato = _formato_botao(botao, app, publico, pub_cfg, r["botao_cfg"])
    if botao.startswith("push_"):
        try:
            irmaos = store.pushes_irmaos(app, publico, tema, botao)
        except Exception:
            irmaos = {}
        if irmaos:
            linhas = "\n".join(f'- ({b.replace("push_", "")}) "{t}"' for b, t in irmaos.items())
            formato += ("\n\nJÁ EXISTEM estes pushes para o mesmo dia/tema — comece de forma "
                        "DIFERENTE e varie o tom; NÃO repita a abertura nem o bordão deles:\n" + linhas)

    subs = {
        "{{RAG_TRECHOS}}": _rag_trechos(app, tema),
        "{{APP_NOME}}": app_cfg["nome"],
        "{{APP_LINHA}}": app_cfg["linha"],
        "{{PUBLICO_ROTULO}}": pub_cfg["rotulo"],
        "{{BOTAO_ROTULO}}": (r["botao_cfg"] or {}).get("rotulo", botao),
        "{{TEMA}}": tema,
        "{{PERFIL_PUBLICO}}": _perfil_publico(pub_cfg),
        "{{FORMATO_BOTAO}}": formato,
        "{{REGRAS_RELIGIAO}}": _bloco_religiao(app, publico),
        "{{REGRA_DIMINUTIVOS}}": regra_dim,
        "{{FEWSHOT_POSITIVOS}}": fewshot_pos,
        "{{FEWSHOT_NEGATIVOS}}": fewshot_neg,
    }
    out = TEMPLATE
    for k, v in subs.items():
        out = out.replace(k, v)
    # remove comentários do template (<!-- ... -->) e colapsa linhas em branco extras
    out = re.sub(r"<!--.*?-->", "", out, flags=re.DOTALL)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def build_user(app: str, publico: str, botao: str, tema: str, dia: int | None = None) -> str:
    rotulo = (config.matriz()["botoes"].get(botao) or {}).get("rotulo", botao)
    dia_txt = f"Dia {dia} — " if dia else ""
    return (f"Gere o conteúdo do '{rotulo}' para o app {config.matriz()['apps'][app]['nome']}, "
            f"público {publico.upper()}, tema: {dia_txt}{tema}.")
