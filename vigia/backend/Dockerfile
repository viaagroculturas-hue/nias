FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema (PostGIS + GDAL + compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar deps Python antes de copiar código (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuário não-root
RUN useradd -m -u 1000 vigia && chown -R vigia:vigia /app
RUN chmod +x /app/entrypoint.sh
USER vigia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/api/ping || exit 1

CMD ["/app/entrypoint.sh"]
