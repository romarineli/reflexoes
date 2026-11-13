"""Monta o system prompt e a mensagem de geração a partir da config resolvida."""
from __future__ import annotations

import json
import re
import zlib
from pathlib import Path

from . import config, store
from .rag import retrieve

BASE = Path(__file__).parent
TEMPLATE = (BASE / "prompts" / "system_base.md").read_text(encoding="utf-8")
FEWSHOT_POS = (BASE / "fewshot" / "positivos.md").read_text(encoding="utf-8")
FEWSHOT_NEG = (BASE / "fewshot" / "negativos.md").read_text(encoding="utf-8")

# Ferramentas escritas À MÃO pelo próprio Augusto (recebidas em 30/10/2026). São o padrão de
# referência de força e formato: entram no few-shot ANTES de qualquer outro exemplo.
try:
    _MAO = json.loads((BASE / "fewshot" / "mao_augusto.json").read_text(encoding="utf-8"))["dias"]
except Exception as e:  # resiliente: sem o arquivo, segue com o few-shot antigo
    print(f"[fewshot] padrão à mão indisponível: {e}", flush=True)
    _MAO = []


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


def _fewshot_mao(botao: str, tema: str, publico: str = "", n: int = 2) -> str:
    """Exemplos do punho do Augusto para ESTE botão, girados de forma estável pelo tema.

    São poucos de propósito: servem de régua de tom e tamanho, não de banco de texto.
    Só entram os que CABEM no limite de caracteres vigente — senão o prompt pediria 460
    caracteres mostrando exemplos de 700, e o modelo seguiria o exemplo.
    """
    exemplos = [(d["dia"], d["titulo"], d["blocos"][botao]) for d in _MAO if botao in d["blocos"]]
    lim = config.limite_chars(publico, botao) if publico else None
    if lim:
        cabem = [e for e in exemplos if len(e[2]) <= lim]
        exemplos = cabem or sorted(exemplos, key=lambda e: len(e[2]))[:n]
    if not exemplos:
        return ""
    i = zlib.crc32((tema or "").encode("utf-8")) % len(exemplos)
    escolhidos = [exemplos[(i + k) % len(exemplos)] for k in range(min(n, len(exemplos)))]
    corpo = "\n\n".join(
        f"**Dia {dia} — {titulo}** ({len(txt)} caracteres)\n{txt}" for dia, titulo, txt in escolhidos
    )
    return ("### PADRÃO DE REFERÊNCIA — escrito à mão pelo próprio Augusto Cury\n"
            "Esta é a régua. Reproduza a força, a concretude e **o tamanho** destes exemplos; "
            "não copie o conteúdo deles.\n\n" + corpo)


def _fewshot_dinamico(app: str, publico: str, botao: str, tema: str = "") -> tuple[str, str]:
    """Anexa aos exemplos fixos os exemplos recém-curados pela Letícia (do banco).

    Resiliente: qualquer falha no banco devolve só os exemplos fixos.
    """
    pos, neg = FEWSHOT_POS, FEWSHOT_NEG
    mao = _fewshot_mao(botao, tema, publico)
    if mao:
        pos = mao + "\n\n---\n\n" + pos
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


# Ângulos de abertura do push de ausência — rotação determinística pelo tema, para que a
# pessoa (que recebe esse push a cada ausência) nunca veja sempre a mesma fórmula.
_ABERTURAS_AUSENTE = [
    "comece pelo CONVITE ao tempo para si (ex.: 'Reserve um minuto...', 'Um minuto só seu...')",
    "comece pela PRÁTICA QUE A ESPERA no app (ex.: 'Tem um exercício esperando por você...')",
    "comece por uma PERGUNTA CURTA dirigida a ela (sem usar a fórmula 'Que tal...')",
    "comece pela PORTA ABERTA / o app continuar ali por ela, e só depois faça o convite",
    "comece pelo que ela GANHA ao voltar (uma mente mais leve, um minuto de calma)",
]


def _abertura_ausente(tema: str) -> str:
    """Ângulo de abertura do push de ausência, girado de forma estável pelo tema do dia."""
    i = zlib.crc32((tema or "").encode("utf-8")) % len(_ABERTURAS_AUSENTE)
    return _ABERTURAS_AUSENTE[i]


# Parágrafos sugeridos por profundidade do público (reflexão da Gestão da Emoção)
_PARAGRAFOS = {"alta": "3 a 4 parágrafos", "media": "2 a 3 parágrafos", "baixa": "2 a 3 frases simples e visuais"}


def _formato_botao(botao: str, app: str, publico: str, pub_cfg: dict, botao_cfg: dict | None,
                   tema: str = "") -> str:
    rotulo = (botao_cfg or {}).get("rotulo", botao)
    prof = pub_cfg.get("profundidade", "media")
    is_kids = "historia" in pub_cfg["botoes"]

    # Tipos CURTOS com limite de caracteres
    lim = (botao_cfg or {}).get("max_chars")
    if botao == "boas_vindas":
        return (f"**{rotulo}** — Gere UMA única frase curta para a tela inicial: de impacto, "
                f"acolhedora, reflexiva e humanizada. **No máximo {lim} caracteres.** "
                "Sem aspas, sem emojis, sem pergunta. Apenas a frase.")
    if botao == "push_ausente":
        return (f"**{rotulo}** — Gere o texto de UMA notificação push de REENGAJAMENTO, para "
                "quem está há alguns dias sem abrir o app.\n"
                "Esta notificação é de OUTRA CATEGORIA — ela NÃO é o push do dia e NÃO entrega "
                "conteúdo nem reflexão. Ela faz uma coisa só: CHAMAR a pessoa de volta.\n"
                "Precisa conter OBRIGATORIAMENTE os dois elementos:\n"
                "1. o convite a reservar um minuto só para ela (um minuto já basta);\n"
                "2. a chamada para ABRIR O APP e fazer a prática / o exercício da mente que "
                "está esperando por ela.\n"
                "Tom: acolhedor e gentil, SEM culpa e SEM cobrança (nada de 'sentimos sua "
                "falta' em tom de dívida, 'você sumiu', 'faz tempo que você não aparece') — "
                "como quem deixa a porta aberta, não como quem cobra presença.\n"
                "NÃO desenvolva o tema do dia nem o cite literalmente: quem está dias fora não "
                "acompanhou os temas. O tema serve, no máximo, como inspiração do que a espera "
                "lá dentro.\n"
                f"ABERTURA DESTA VEZ — {_abertura_ausente(tema)}. A pessoa recebe este push "
                "toda vez que fica dias fora, então ele NÃO pode ter bordão: siga o ângulo de "
                "abertura indicado e não repita fórmula de outras gerações.\n"
                "TAMANHO — notificação de celular corta o texto: escreva CURTO.\n"
                f"Ideal entre 55 e 75 caracteres; **nunca passe de {lim}**. UMA frase só "
                "(no máximo duas de poucas palavras), sem subordinada e sem explicação.\n"
                "Os primeiros ~60 caracteres precisam já conter o convite E a chamada para "
                "abrir o app: o que vier depois pode nem aparecer na tela.\n"
                "Corte o que não é essencial: adjetivo decorativo, 'que deixa sua mente mais "
                "leve', 'quando quiser', repetição da mesma ideia em outras palavras.\n"
                "Sem aspas, sem emojis. Apenas o texto da notificação.")
    if botao.startswith("push_"):
        periodo = (botao_cfg or {}).get("periodo", "")
        return (f"**{rotulo}** — Gere o texto de UMA notificação push para o período: "
                f"**{periodo}**, conectada ao tema do dia: curta, acolhedora e que convide a "
                f"abrir o app. **No máximo {lim} caracteres** (precisa caber na notificação). "
                "Uma frase, sem aspas, sem emojis. Apenas o texto da notificação.")

    if botao == "gestao_emocao":
        lim = pub_cfg.get("reflexao_max_chars")
        limtxt = (f" O texto inteiro deve ter NO MÁXIMO {lim} caracteres." if lim else "")
        return (
            f"**{rotulo}** — Gere SOMENTE a reflexão central do dia: {_PARAGRAFOS.get(prof)}, "
            f"**parágrafos curtos (2 a 3 frases cada)**.{limtxt}\n"
            "ESTRUTURA (é a do punho do Augusto, siga sem inventar outra):\n"
            "1. abertura concreta — uma situação, uma cena, uma afirmação direta; nunca "
            "diagnóstico de época ('vivemos numa sociedade...', 'a humanidade...');\n"
            "2. no MEIO do texto, **DUAS perguntas provocativas**, uma por linha, dirigidas "
            "diretamente à pessoa ('você'). Não são retóricas: têm que incomodar;\n"
            "3. fechamento em AFIRMAÇÃO que reposiciona a ideia — **não termine com pergunta**, "
            "as perguntas já foram feitas no meio.\n"
            "Leitura de cerca de um minuto. Prefira a frase curta e dura à frase longa e morna.\n"
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
        limex = config.limite_chars(publico, botao)
        return (
            f"**{rotulo}** — Gere a prática aplicável do dia: UMA prática concreta e curta "
            "(no MÁXIMO duas opções — NÃO liste três ou mais). "
            "FINALIZE com uma breve pergunta de reflexão ligada a esta prática."
            + (f"\n**No máximo {limex} caracteres**, contando espaços." if limex else "")
            + "\nNÃO reescreva a reflexão da Gestão da Emoção."
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
        limcn = config.limite_chars(publico, botao)
        return (
            f"**{rotulo}** — Gere SOMENTE 1 a 2 frases de fechamento do dia, acolhedoras e "
            f"ritualísticas, reforçando o tema.{extra} Sem exercício e sem pergunta provocativa."
            + (f" **No máximo {limcn} caracteres**, contando espaços — cabe pouco, "
               "escolha a frase certa em vez de somar frases." if limcn else "")
        )

    if botao == "desafio":
        return (f"**{rotulo}** — Gere uma ação concreta e executável ligada ao tema do dia e "
                "FINALIZE com uma pergunta de reflexão associada ao desafio.")

    # fallback (historia gerada isoladamente, se pedida)
    return f"**{rotulo}** — {(botao_cfg or {}).get('descricao', '')}"


def build_system(app: str, publico: str, botao: str, tema: str,
                 evitar_perguntas: list[str] | None = None) -> str:
    r = config.resolve(app, publico, botao)
    app_cfg, pub_cfg = r["app_cfg"], r["pub_cfg"]

    regra_dim = ""
    if app and publico in config.glossario()["diminutivos"]["proibido_para"]:
        regra_dim = ("- NUNCA use diminutivos (corpinho, mãozinha, olhinhos, etc.) — "
                     "este público não permite.")

    fewshot_pos, fewshot_neg = _fewshot_dinamico(app, publico, botao, tema)

    formato = _formato_botao(botao, app, publico, pub_cfg, r["botao_cfg"], tema)
    if botao.startswith("push_"):
        try:
            irmaos = store.pushes_irmaos(app, publico, tema, botao)
        except Exception:
            irmaos = {}
        if irmaos:
            linhas = "\n".join(f'- ({b.replace("push_", "")}) "{t}"' for b, t in irmaos.items())
            if botao == "push_ausente":
                formato += ("\n\nEstes são os pushes DIÁRIOS deste dia/tema. O seu é de outra "
                            "categoria (reengajamento): NÃO soe como uma variação deles — nem a "
                            "abertura, nem o bordão, nem a mesma promessa de conteúdo:\n" + linhas)
            else:
                formato += ("\n\nJÁ EXISTEM estes pushes para o mesmo dia/tema — comece de forma "
                            "DIFERENTE e varie o tom; NÃO repita a abertura nem o bordão deles:\n" + linhas)

    # Cada dia é gerado isolado, então o modelo não sabe o que já escreveu nos dias vizinhos
    # e cai no mesmo molde de pergunta ("Quando foi a última vez que você..."). Lido um dia por
    # dia não incomoda; lido em sequência, como a curadoria lê, fica evidente. Por isso as
    # perguntas já usadas entram no prompt como lista do que NÃO repetir.
    if evitar_perguntas:
        usadas = "\n".join(f"- {q}" for q in evitar_perguntas)
        formato += ("\n\nESTAS PERGUNTAS JÁ FORAM USADAS em outros dias deste mesmo ciclo. "
                    "Não repita nenhuma delas e, principalmente, **não repita a forma de "
                    "abrir a pergunta** (as primeiras palavras). Procure outro ângulo:\n"
                    + usadas)

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
