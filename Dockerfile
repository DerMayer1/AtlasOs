FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "atlas.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
