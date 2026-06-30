FROM python:3.12-slim

# Install system utilities needed for runtime execution (e.g., git/curl if required, clean footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv cleanly using the official optimized multi-stage binary copy method
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR /app

# Enable bytecode compilation for optimal container startup latency
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Synchronize dependencies using lock file tracking
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

# Copy active production application space
COPY main.py /app/
COPY core/ /app/core/
COPY infra/ /app/infra/
COPY scripts/ /app/scripts/
COPY industry-config.json /app/


EXPOSE 8000

CMD ["uv", "run", "python", "main.py"]
