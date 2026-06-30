FROM python:3.14-alpine

# Install build dependencies for compiling Python packages (e.g. Stan, scipy, prophet)
RUN apk add --no-cache gcc g++ musl-dev python3-dev libffi-dev libstdc++ gfortran openblas-dev

# Install uv natively
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency configuration and lockfile
COPY pyproject.toml uv.lock ./

# Synchronize python dependencies exactly from lockfile
RUN uv sync --frozen

# Copy source files
COPY main.py ./
COPY core/ ./core/
COPY infra/ ./infra/
COPY scripts/ ./scripts/
COPY industry-config.json ./

# Expose backend port
EXPOSE 8000

# Execute server using uvicorn via uv run context
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
