# Imagen mínima para ApuestaEdge (FastAPI + SQLite).
FROM python:3.12-slim

# Trabajamos en /app; sin caché de pip para imágenes más ligeras.
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY data ./data
COPY tests ./tests

# La BD vive en el volumen /data (persistente en Render/Fly). Los JSON de la
# imagen pueden quedar tapados por un volumen montado: config.asset_path()
# hace fallback a /app/data incluido en el repo.
ENV APUESTAEDGE_DATA_DIR=/data
RUN mkdir -p /data && cp data/*.json /data/

EXPOSE 8000

# $PORT lo fija Render/Fly; uvicorn escucha en 0.0.0.0 dentro del contenedor.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
