# --- builder ---
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
WORKDIR /app

# Install system deps for rasterio, geopandas (GDAL, etc.) before uv sync
RUN apt-get update && apt-get install -y --no-install-recommends \
  gdal-bin libgdal-dev gcc g++ build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-install-project --no-dev
COPY app /app/app

# --- final ---
FROM python:3.11-slim-bookworm

# Install GDAL runtime dependency
RUN apt-get update && apt-get install -y --no-install-recommends gdal-bin && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
