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

# Copy uv binary from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

COPY --from=builder /app /app

# Copy and set permissions for entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
ENTRYPOINT ["/app/entrypoint.sh"]
