# Regras de geração — fonte da verdade (humana)

> Versão legível das regras. A versão verificável em código está em
> [`glossario.yaml`](glossario.yaml). A matriz app × público × botão está em
> [`matriz.yaml`](matriz.yaml). Tudo derivado de **`01.COMANDOS.docx`** (correções
> da Letícia) e **`Considerações IA.docx`**.

## Princípio essencial

Todo texto precisa ser **humanizado, reflexivo, com fala próxima, acolhedora e inspiradora**.
O leitor deve sentir: *"isso me ajudou hoje"*, *"isso me fez pensar"*, *"isso mudou uma
atitude minha"*, *"amanhã quero continuar"*, *"estou evoluindo emocionalmente"*.

Trabalhamos com **"textos reflexivos"**, nunca "frases" — o termo "frase" faz o modelo
encurtar literalmente a saída.

## Estrutura por dia/botão

Padrão para todos os dias e botões: **Reflexão + Exercício + Pergunta provocativa**.
Os textos podem **variar de tamanho** entre os dias (uns mais curtos, outros mais longos)
para não ficarem repetitivos — mas com **parágrafos curtos (2–3 frases)** para boa leitura no
celular. A reflexão (Gestão da Emoção) tem **limite de caracteres por público** (em
`matriz.yaml → reflexao_max_chars`): Adultos ~850, Teens ~650, Kids ~400. Frase do dia ≤120,
push ≤140. Os limites são enforçados (instrução + validação + regeneração se estourar).

## Aprendizados da curadoria (já aplicados como regra)

Vindos das rodadas de revisão da Letícia — fixados no prompt porque few-shot sozinho não
garante:
- **Reflexão mais curta** (limite por público acima) — pedido "muito extenso, diminuir".
- **Pushes do mesmo dia variam** entre si: manhã/tarde/noite não repetem abertura/bordão
  (ex.: não repetir "Vem ver"/"Vem descobrir"). O gerador recebe os outros pushes do dia.
- **Exercício Antiestresse = 1 prática (máx 2)**, nunca 3 ou mais.
- **LifeCalm · Calma Noturna (Adultos)** traz referência ao Mestre dos Mestres / mestre do amor.
- **Exercício Antiestresse** e **Desafio (Kids)** terminam com uma **pergunta de reflexão**
  ligada à própria prática/desafio.

## Regras duras de vocabulário (proibições)

1. **Nunca** "inteligência emocional" / "emocionalmente inteligente" — é o oposto da teoria
   de Cury. Usar "pessoas inteligentes", "pessoas emocionalmente saudáveis", "maturidade",
   "sabedoria". Substituir "Inteligência Emocional" por **"Gestão da Emoção"**.
2. **Nunca** a técnica de "contar até cinco/três" antes de responder. Usar a variação:
   *respire profundamente três vezes e pergunte: "Vale a pena perder minha paz por isso?"*
3. **Nunca** o termo "Mindfulness". Usar "respiração profunda", "desacelerar a mente",
   "desacelerar os batimentos cardíacos".
4. **Nunca** diminutivos nos textos de **Kids** (corpinho, mãozinha, etc.).

## Regras de religião (dependem de app + público)

- **LifeCalm (cristão) · Adultos:** **nunca** "Deus", "Cristo", "Jesus", "Carpinteiro de
  Nazaré". Usar "o Mestre dos Mestres", "o Homem mais Inteligente da História", "o Maior
  Líder da História", "o mestre do amor", "o mestre da emoção".
- **LifeCalm (cristão) · Teens e Kids:** usar **somente** "Jesus Cristo" (de forma leve em
  Kids, que a criança pequena entenda).
- **SpotCalm (geral):** **sem** referências religiosas. *(Confirmar com a Letícia como
  substituir a figura do "mestre da emoção" por linguagem secular.)*

## Estilo e anti-repetição

- Usar termos **positivos**: em vez de "enfraquece", usar "compromete".
- Variar **"mente"**, não só "coração".
- **Reduzir** expressões que aparecem demais: "fortalece a emoção", "protege a emoção",
  "coração mais feliz", "desacelerar", "respire fundo", "paz emocional".
- **Diversificar** temas: gratidão, esperança, propósito, perdão, coragem, confiança,
  autocompaixão, serenidade.

## Diferenciação por público

- **Adultos:** maior profundidade. Variar os exercícios (diário emocional, oração curta,
  ato de reconciliação, pausa de silêncio, análise de pensamento, carta não enviada,
  prática de gratidão, renúncia a uma reação impulsiva).
- **Teens:** **não** ser o texto adulto simplificado. Entrar no universo jovem real:
  redes sociais, comparação de corpo, grupo de amigos, exclusão, pressão por desempenho,
  medo de errar, conflitos com pais, validação, telas/jogos.
- **Kids:** cotidiano infantil (escola, brinquedo, dividir, pedir desculpas). Calma Noturna
  = texto reflexivo + **história** (personagens de nomes bíblicos) + **desafio** executável.
  Leitura próxima e visual.

## Conceitos do método a incorporar (Gestão da Emoção)

Ao longo dos dias, em linguagem adaptada: "Eu como gestor da emoção", "Filtrar estímulos
estressantes", "Proteger a janela da memória", "Gerenciar pensamentos", "Autodiálogo",
"Mesa-redonda do eu", "Construção da autoestima", "Fenômeno RAM".

## Diretrizes de produto (Considerações IA) — para a evolução

Não bloqueiam a geração v1, mas guiam a calibração:
- **Nomear as técnicas** (ex.: "Pausa dos 3 Respirares", "Escuta do Coração", "Jardim dos
  Pensamentos") — aumenta valor percebido.
- **Jornada com fases/semanas temáticas** (progresso visível), não dias soltos.
- **Check-in antes/depois** do exercício (estado emocional → resultado percebido).
- **Micro-oração opcional** (só LifeCalm).
- **Calma Noturna como ritual** de fechamento, mais envolvente.
- **Desafios executáveis e mensuráveis**, não abstratos.

## Pendências a confirmar com a curadoria

- [ ] Substituição secular da figura do "mestre da emoção" no **SpotCalm (geral)**.
- [ ] Grafia/identidade final dos apps e qual linha pertence a cada um (assumido:
      SpotCalm = geral, LifeCalm = cristão).
- [ ] Lista oficial de temas por dia / jornada (há `365_temas_gestao_emocao...pdf` no material).
