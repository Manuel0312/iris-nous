FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BCI_IOT_HTTPS=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
RUN pip install --no-cache-dir -e .

RUN mkdir -p /data/profiles /data/photos

ENV BCI_IOT_DATA_DIR=/data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn bci_iot.web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
