FROM python:3.11-slim

WORKDIR /app

# System deps for lxml and other C-extension packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

# Source is mounted as a volume in docker-compose for hot-reload.
# Copy here so the image is self-contained for production use.
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
