FROM node:22-alpine AS frontend-build

WORKDIR /frontend
RUN npm install --global pnpm@10.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY --from=frontend-build /src/atlas/interfaces/api/spa ./src/atlas/interfaces/api/spa
COPY migrations ./migrations
COPY scripts ./scripts
RUN uv sync --locked --no-editable --no-dev --no-cache

EXPOSE 8000
CMD ["uvicorn", "atlas.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
