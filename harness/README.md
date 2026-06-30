# Harness de Geração — Textos Reflexivos (SpotCalm / LifeCalm)

Fundação do sistema de geração de textos reflexivos dos apps de bem-estar emocional do
Fernando Tamaso, baseados na obra de Augusto Cury. Esta pasta é a **fonte da verdade
declarativa** — calibrar o sistema é editar config + exemplos, sem mexer em código.

> Contexto e arquitetura completa: `../briefing-projeto-reflexoes.md` e
> `../plano-harness-reflexoes.md`. Material-fonte em `../material/`.

## Estrutura

```
harness/
├── config/
│   ├── matriz.yaml      # app × público × botão (camadas de config) + params de geração
│   ├── glossario.yaml   # proibições/substituições DURAS (verificáveis em código)
│   ├── regras.md        # versão legível das regras (de 01.COMANDOS.docx)
│   └── formato.md       # spec de formato por botão (dos textos aprovados)
├── prompts/
│   └── system_base.md   # template do system prompt (tokens {{...}} preenchidos pelo harness)
└── fewshot/
    ├── positivos.md     # formato e tom a seguir (Adultos aprovados, limpos)
    └── negativos.md     # ❌→✅ violações reais com a correção
```

## Como uma geração se monta (visão do harness)

Para um pedido `(app, público, botão, tema/dia)`:

1. Resolve a config em camadas: **global → app → público → botão** (`matriz.yaml`).
2. Monta o **system prompt** (`prompts/system_base.md`) preenchendo os tokens:
   - perfil do público, spec do botão (`formato.md`), bloco de religião condicional e
     regra de diminutivos (`glossario.yaml`), few-shot (`fewshot/`).
   - *(Fase 2)* trechos recuperados do RAG dos livros como fundamento.
3. Gera com o provider configurado (**Anthropic / Claude**, `matriz.yaml → geracao`).
4. *(Fase 2)* **Validação automática**: regras duras do `glossario.yaml` (regex/contains)
   → reprova e regenera; depois juiz LLM de tom.
5. *(Fase 3)* Vai para a **fila de aprovação** (cards gostei/não gostei da Letícia);
   aprovados alimentam `fewshot/positivos`, reprovados alimentam `fewshot/negativos`.

## Decisões já travadas

- **Apps:** SpotCalm = geral · LifeCalm = cristão.
- **Provider inicial:** Anthropic / Claude.
- **Insight-chave:** textos aprovados = referência de **formato/tom**; `01.COMANDOS.docx` =
  **regras duras** ainda não aplicadas neles. Por isso o few-shot é positivo **e** negativo.

## Pendências de curadoria (ver `config/regras.md`)

- [ ] Substituição secular da figura do "mestre da emoção" no SpotCalm (geral).
- [ ] Exemplos positivos limpos de Teens, Kids e SpotCalm.
- [ ] Lista oficial de temas/jornada por dia (há `365_temas...pdf` no material).

## Como rodar

**Setup (uma vez):**
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# a chave fica em .env (ANTHROPIC_API_KEY=...), protegida por .gitignore
```

**CLI — geração / experimentos:**
```bash
PYTHONPATH=. .venv/bin/python -m harness.run --experimento   # 10 textos-teste do Arquivo 2
PYTHONPATH=. .venv/bin/python -m harness.run --app lifecalm --publico adultos \
    --botao gestao_emocao --dia 12 --tema "A importância da calma"
```

**Interface de curadoria (Letícia) — web:**
```bash
PYTHONPATH=. .venv/bin/uvicorn harness.api:app --port 8000
# abrir http://localhost:8000
```
A interface permite: gerar texto (por botão ou **dia completo**), ver a validação de regras
duras, e revisar em **cards** marcando 👍 gostei / 🤔 com ressalva / 👎 não gostei + comentário.
O botão **Exportar few-shot** baixa no navegador um `few-shot-curado.md` com aprovados e
reprovados (cópia legível/versionável). O loop de feedback NÃO depende disso — ele lê os
curados direto do banco a cada geração; o export é só para inspeção/arquivo.

Componentes: `api.py` (FastAPI), `store.py` (SQLite em `saidas/curadoria.db`),
`webui/index.html` (front).

## Loop de feedback (ativo)

O ciclo de melhoria está **fechado**: ao gerar, `prompt.py` busca no banco (`store.fewshot_curado`)
os exemplos recém-curados pela Letícia — aprovados (gostei/ressalva) do mesmo app+público+botão
viram exemplos positivos; reprovados (não gostei) do mesmo app+público viram negativos, com o
comentário dela junto. Cada rodada de revisão melhora a geração seguinte, sem mexer em código.
Resiliente: se o banco falhar, cai nos exemplos fixos de `fewshot/`.

## RAG (ativo — Fase 2)

Os textos são fundamentados na obra real do Cury via recuperação semântica:
- Pipeline offline em `rag/`: `ingest.py` (12 PDFs → 987 chunks) → `embed.py` (Vertex AI
  `text-multilingual-embedding-002`, 768-dim) → `load_pg.py` (carga no **pgvector**, índice HNSW).
- No serving, `rag/retrieve.py` embeda o tema e busca os trechos mais próximos (filtro de linha:
  LifeCalm usa cristo+geral, SpotCalm só geral) → injetados no prompt em `{{RAG_TRECHOS}}`.
- Resiliente: sem Postgres/Vertex, gera sem fundamento (não quebra). Log `[RAG] N trecho(s)`.

Re-ingestão (quando trocar livros): `PYTHONPATH=. .venv/bin/python -m harness.rag.ingest`
então `... -m harness.rag.embed` e `PGPW=... ... -m harness.rag.load_pg` (via Cloud SQL proxy).

## API de entrega (consumida pelo backend do app)

Só conteúdo **aprovado** pela curadoria (gostei/ressalva) é servido. Auth máquina-a-máquina
por header `x-api-key` (secret `CONTENT_API_KEY`); a UI/curadoria segue em HTTP Basic.

- `GET /content/daily?app=&publico=&dia=` → blocos aprovados do dia (o mais recente por botão).
  404 se nada aprovado ainda. As regras de horário/perfil/quantidade ficam no app.
- `GET /content/status?app=&publico=` → cobertura: quais dias têm conteúdo e quais estão completos.

Geração em lote antecipada (pré-preenche dias à frente como pendentes de revisão):
`DATABASE_URL=<proxy> PYTHONPATH=. .venv/bin/python -m harness.run --lote --app lifecalm --dias 7`

## Próximos passos

- Calibração com a Letícia (rodadas de revisão no homolog) até a taxa de aprovação alvo.
- Definir com a curadoria a versão secular do SpotCalm (geral) e a lista oficial de temas/dia.
- Integração do backend do app com a API de entrega; geração em lote agendada (cron).
