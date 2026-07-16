FROM node:22-alpine AS frontend-build

WORKDIR /frontend
RUN npm install --global pnpm@10.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY --from=frontend-build /src/atlas/interfaces/api/spa ./src/atlas/interfaces/api/spa
COPY migrations ./migrations
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "atlas.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
