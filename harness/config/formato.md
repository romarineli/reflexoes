# Spec de formato por botão (derivada dos textos aprovados)

> Referência: `02.Revisada - LifeCalm (Cristo).docx` (Dias 12–14). Define o **formato**
> e o **tom** — as regras de vocabulário do [`regras.md`](regras.md) prevalecem sobre
> qualquer coisa observada nos exemplos (os aprovados ainda têm violações a corrigir).

Cada **dia** tem um **tema** (ex.: "A importância da calma", "Aprender a ouvir",
"Respeitar os próprios limites") e é gerado para os 3 públicos.

---

## Botão — Gestão da Emoção

Reflexão central do dia. Termina **sempre** com uma pergunta provocativa.

- **Adultos:** 3–4 parágrafos curtos, profundidade emocional. Pode abrir com a figura de
  referência (LifeCalm: "O mestre da emoção demonstrava…"). Fecha com pergunta.
  > *Você costuma reagir impulsivamente ou agir com equilíbrio?*
- **Teens:** 2–3 parágrafos diretos, ancorados no universo jovem. Fecha com pergunta.
  > *Você costuma agir no impulso ou pensar antes de responder?*
- **Kids:** 2–3 frases simples e visuais. Fecha com pergunta leve.
  > *Você já tentou respirar fundo quando ficou irritado?*

## Botão — Exercício Antiestresse

Prática aplicável do dia.

- **Adultos:** instrução prática; pode oferecer **opções** ("escolha uma destas…").
  Variar o tipo de exercício entre os dias (ver `matriz.yaml` → `exercicios_preferidos`).
- **Teens:** instrução curta e concreta, sem peso ("ouça alguém sem interromper, sem mexer
  no celular").
- **Kids:** formato família —
  ```
  Querida família, [proposta da prática lúdica com nome].
  Como aplicar: "[instrução em fala direta para a criança]".
  Por que funciona: [benefício emocional em 1 linha].
  ```

## Botão — Calma Noturna

Fechamento do dia / desaceleração. Breve, acolhedor, ritualístico.

- **Adultos / Teens:** 1–2 frases de encerramento que reforçam o tema do dia.
- **Kids:** frase de relaxamento sensorial ("Seu corpo está relaxando… sua respiração
  ficando calma…"). **Sem diminutivos.** Em Kids, este botão também aciona a **História**
  e o **Desafio** abaixo.

## HISTÓRIA (apenas Kids)

Narrativa curta (4–7 frases) com:
- **Personagem de nome bíblico** (Lucas, Samuel, Maria, Davi, Pedro…).
- Situação do **cotidiano infantil** ligada ao **tema do dia**.
- Em LifeCalm: referência leve a **"Jesus Cristo"** como modelo de atitude.
- Lição emocional implícita/explícita ao final.

> *Pedro ficou bravo porque o amigo quebrou seu brinquedo… lembrou que Jesus Cristo
> ensinava a pensar antes de agir… respirou fundo e conversou… os dois se abraçaram.*

## Desafio (apenas Kids)

Uma ação **concreta e executável**, ligada ao tema.

> *Quando ficar irritado, respire profundamente três vezes antes de responder. Descubra
> como a calma pode ser mais forte do que a raiva.*

---

## Boas-vindas (tela inicial)

Frase **única**, curta, de impacto, acolhedora, reflexiva e humanizada. Uma por entrega.

## Push notifications

Texto curto por período (manhã / tarde / noite), no mesmo tom. As regras de horário,
quantidade e perfil ficam **na aplicação**; o harness só gera o texto sob demanda.

---

## Esquema de saída (JSON sugerido para a API)

```json
{
  "app": "lifecalm",
  "publico": "kids",
  "dia": 12,
  "tema": "A importância da calma",
  "blocos": {
    "gestao_emocao": "…",
    "exercicio_antiestresse": "…",
    "calma_noturna": "…",
    "historia": { "titulo": "…", "texto": "…" },
    "desafio": "…"
  }
}
```
Para Adultos/Teens, `blocos` traz apenas `gestao_emocao`, `exercicio_antiestresse`,
`calma_noturna`.
