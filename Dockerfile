# Minimal uv-based image. Defaults to the streamable-HTTP transport.
FROM python:3.13-slim

# uv (and uvx) from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY . .

# Install only runtime deps into a project venv.
RUN uv sync --no-dev

ENV JMC_TRANSPORT=http \
    JMC_HOST=0.0.0.0 \
    JMC_PORT=3011
# Multi-user HTTP: confine writes and read the token per request from the
# X-Registry-Token header rather than from a container-wide env var.
# ENV JMC_WORKSPACE=/work

EXPOSE 3011

CMD ["uv", "run", "just-module-creator", "http", "--host", "0.0.0.0", "--port", "3011"]
