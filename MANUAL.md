# Manual de Instalação — Reflexões (SpotCalm / LifeCalm)

Serviço que **gera os textos reflexivos dos apps por IA**, com uma **tela de curadoria**
(revisar/aprovar) e uma **API** que o app consome. Este pacote tem tudo: código, a base dos
livros já processada (RAG) e este manual.

---

## 1. O que você precisa

- **Python 3.12+** (ou **Docker**)
- Um **banco de dados**: MySQL/MariaDB **ou** PostgreSQL (pode ser um RDS que já exista)
- Uma **chave da Anthropic** → https://console.anthropic.com
- Credencial para os **embeddings** (escolha um): **Bedrock** (AWS) · **Vertex** (GCP) · **OpenAI**

---

## 2. Rodar local em 3 comandos (teste rápido, usa SQLite)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # edite e preencha (ver seção 3)
PYTHONPATH=. .venv/bin/uvicorn harness.api:app --port 8000
```
Abra **http://localhost:8000** → login com `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` do `.env`.

---

## 3. Configurar — o arquivo `.env`

Copie `.env.example` para `.env` e preencha. São poucas variáveis:

| Variável | O que é | Exemplo |
|---|---|---|
| `ANTHROPIC_API_KEY` | chave da Anthropic (vem deles) | `sk-ant-...` |
| `DATABASE_URL` | conexão do seu banco (vazio = SQLite local) | `mysql://user:senha@host:3306/curadoria` |
| `EMBED_PROVIDER` | provedor de embeddings | `bedrock` · `vertex` · `openai` |
| `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` | login da tela de curadoria (você escolhe) | `admin` / `umaSenhaForte` |
| `CONTENT_API_KEY` | chave da API do app (você gera) | `openssl rand -hex 32` |

**Embeddings, conforme o provedor:**
- **Bedrock (AWS):** `EMBED_PROVIDER=bedrock`, `AWS_REGION=us-east-1`, `EMBED_DIM=1024`, e a role/credencial AWS com `bedrock:InvokeModel`.
- **Vertex (GCP):** `EMBED_PROVIDER=vertex` e credencial GCP no ambiente (service account).
- **OpenAI:** `EMBED_PROVIDER=openai` e `OPENAI_API_KEY=...`.

---

## 4. Ligar a base dos livros (RAG) — **já vem pronta**

Os 987 trechos dos livros já estão no pacote (`saidas/rag_corpus*.jsonl`). **Não precisa dos PDFs.**
Só carregue no seu banco:

```bash
# Se EMBED_PROVIDER=vertex (vetores já prontos): rode só
PYTHONPATH=. .venv/bin/python -m harness.rag.load_db

# Se EMBED_PROVIDER=bedrock ou openai: re-gere os vetores (sem PDFs) e carregue
PYTHONPATH=. .venv/bin/python -m harness.rag.embed
PYTHONPATH=. .venv/bin/python -m harness.rag.load_db
```
> Sem isso o sistema ainda gera textos (com as regras), só não usa os trechos dos livros como base.

---

## 5. Colocar no ar (produção)

É **um container + um banco + as variáveis de ambiente**. Build da imagem:

```bash
docker build -t reflexoes .
docker run -p 8080:8080 --env-file .env reflexoes      # teste local do container
```

Depois, suba essa imagem no host de vocês:

- **AWS (recomendado p/ vocês):** **App Runner** ou **ECS/Fargate** apontando para a imagem (ECR);
  banco = **RDS MySQL/MariaDB**; `EMBED_PROVIDER=bedrock`; a task role precisa de `bedrock:InvokeModel`.
- **GCP:** `gcloud run deploy --source .`; banco = Cloud SQL; `EMBED_PROVIDER=vertex`.

O serviço sobe numa **URL**. A curadoria entra por login (usuário/senha); o app consome a API com a chave.

**Carga inicial do RAG** (seção 4): rode uma vez apontando o `DATABASE_URL` para o banco de produção.

---

## 6. Como o app consome (API de entrega)

O backend do app chama estes endpoints com o header `x-api-key: <CONTENT_API_KEY>`:

- `GET /content/daily?app=lifecalm&publico=adultos&dia=12` → blocos **aprovados** do dia.
- `GET /content/status?app=lifecalm&publico=adultos` → quais dias têm conteúdo pronto.

(Só conteúdo aprovado pela curadoria é entregue.)

---

## 7. Ajustar as regras de conteúdo (sem mexer em código)

Tudo de vocabulário, tamanhos e limites está em **`harness/config/`** (arquivos YAML):
`matriz.yaml`, `glossario.yaml`, `regras.md`, `formato.md`. Edite e republique.

---

## Estrutura do pacote

```
harness/        código (API, banco, RAG, geração, regras, tela de curadoria)
saidas/         base dos livros já processada (RAG pronto)
requirements.txt  Dockerfile  .env.example  MANUAL.md
```
