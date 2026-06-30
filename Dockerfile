# Imagem do serviço de curadoria/geração (FastAPI) para Cloud Run.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Dependências primeiro (cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código do harness (config/prompt/fewshot/api). Material pesado e segredos ficam de fora
# via .dockerignore — config e fewshot são leves e entram.
COPY harness/ ./harness/

# Cloud Run injeta a porta em $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn harness.api:app --host 0.0.0.0 --port ${PORT}"]
