FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything needed for pip install (source included)
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy Alembic config and migrations
COPY alembic/ alembic/
COPY alembic.ini .

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
