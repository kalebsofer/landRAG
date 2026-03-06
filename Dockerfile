FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "landrag.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
