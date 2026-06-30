"""CLI do harness.

Exemplos:
  python -m harness.run --app lifecalm --publico adultos --botao gestao_emocao --dia 12 --tema "A importância da calma"
  python -m harness.run --experimento            # gera os 10 textos-teste do Arquivo 2
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

from . import config, generate, store

ROOT = Path(__file__).parent.parent
SAIDAS = ROOT / "saidas"

# Temas reais do Arquivo 2 (02.Revisada - LifeCalm Cristo)
TEMAS_ARQUIVO2 = [
    (12, "A importância da calma"),
    (13, "Aprender a ouvir"),
    (14, "Respeitar os próprios limites"),
    (15, "A força da gentileza"),
    (16, "Aprender a esperar"),
    (20, "A importância de pedir desculpas"),
    (21, "Aprender a agradecer as pessoas"),
    (22, "Aprender a confiar mais em si mesmo"),
    (23, "A importância de ajudar as pessoas"),
    (24, "Cuidar da própria mente"),
]


def gerar_um(app: str, publico: str, botao: str, tema: str, dia: int | None) -> dict:
    return generate.gerar(app, publico, botao, tema, dia)


def _salvar(resultados: list[dict], nome: str) -> Path:
    SAIDAS.mkdir(exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = SAIDAS / f"{nome}-{stamp}"
    base.with_suffix(".json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    # versão legível em markdown
    md = [f"# Experimento — {nome} ({stamp})\n"]
    for r in resultados:
        md.append(f"## {r['app'].upper()} · {r['publico'].upper()} · {r['botao']} "
                  f"· Dia {r['dia']} — {r['tema']}\n")
        md.append(r["texto"] + "\n")
        v = r["validacao"]
        if v["ok"]:
            md.append("\n> ✅ validação de regras duras: OK\n")
        else:
            md.append("\n> ⚠️ violações: " + "; ".join(v["violacoes"]) + "\n")
        md.append("\n---\n")
    base.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    return base


def experimento() -> None:
    """10 textos-teste: LifeCalm, Gestão da Emoção, alternando os 3 públicos."""
    publicos = ["adultos", "teens", "kids"]
    resultados = []
    print("Gerando 10 textos-teste (LifeCalm · Gestão da Emoção)...\n")
    for i, (dia, tema) in enumerate(TEMAS_ARQUIVO2):
        pub = publicos[i % 3]
        print(f"  [{i+1}/10] {pub:8s} · Dia {dia} — {tema}")
        r = gerar_um("lifecalm", pub, "gestao_emocao", tema, dia)
        resultados.append(r)
        flag = "OK" if r["validacao"]["ok"] else "VIOLAÇÕES: " + "; ".join(r["validacao"]["violacoes"])
        print(f"        validação: {flag}\n")
    base = _salvar(resultados, "arquivo2-10textos")
    ok = sum(1 for r in resultados if r["validacao"]["ok"])
    print(f"\nConcluído. {ok}/10 passaram nas regras duras.")
    print(f"Saída: {base.with_suffix('.md')}")


def lote(app: str, publico: str | None, n_dias: int) -> None:
    """Geração em lote antecipada: gera os botões dos próximos dias e PERSISTE no banco
    como pendentes de revisão. Define DATABASE_URL p/ gravar no Postgres da nuvem."""
    store.init()
    pubs = [publico] if publico else ["adultos", "teens", "kids"]
    temas = TEMAS_ARQUIVO2[:n_dias]
    total = ok = 0
    print(f"Lote: app={app} | públicos={pubs} | {len(temas)} dia(s)\n")
    for pub in pubs:
        botoes = config.resolve(app, pub)["pub_cfg"]["botoes"]
        for dia, tema in temas:
            for b in botoes:
                r = gerar_um(app, pub, b, tema, dia)
                store.salvar_item(app, pub, b, dia, tema, r["texto"], r["validacao"])
                total += 1
                ok += int(r["validacao"]["ok"])
                print(f"  {pub:8s} d{dia:<3} {b:22s} {'OK' if r['validacao']['ok'] else 'VIOL'}")
    print(f"\nlote concluído: {total} gerados ({ok} ok nas regras), salvos como pendentes.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Harness de geração de textos reflexivos.")
    ap.add_argument("--experimento", action="store_true", help="gera os 10 textos-teste do Arquivo 2")
    ap.add_argument("--lote", action="store_true", help="geração em lote antecipada (persiste no banco)")
    ap.add_argument("--app", choices=["spotcalm", "lifecalm"])
    ap.add_argument("--publico", choices=["adultos", "teens", "kids"])
    ap.add_argument("--botao", default="gestao_emocao")
    ap.add_argument("--dia", type=int)
    ap.add_argument("--dias", type=int, default=3, help="nº de dias no lote (default 3)")
    ap.add_argument("--tema")
    args = ap.parse_args()

    if args.experimento:
        experimento()
        return
    if args.lote:
        if not args.app:
            ap.error("--lote exige --app (e opcionalmente --publico, --dias)")
        lote(args.app, args.publico, args.dias)
        return
    if not (args.app and args.publico and args.tema):
        ap.error("informe --app, --publico e --tema (ou use --experimento)")
    r = gerar_um(args.app, args.publico, args.botao, args.tema, args.dia)
    print(r["texto"])
    print("\n---\nvalidação:", "OK" if r["validacao"]["ok"] else r["validacao"]["violacoes"])


if __name__ == "__main__":
    main()
