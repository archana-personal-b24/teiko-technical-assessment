FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cell-count.csv load_data.py analyze.py ./
COPY teiko ./teiko
RUN python load_data.py && python analyze.py


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8050
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip
COPY app.py ./
COPY teiko ./teiko
COPY --from=builder /build/cell_counts.db ./cell_counts.db

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8050
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8050')+'/healthz',timeout=2)"
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8050} --workers 2 --threads 2 --timeout 120 app:server"]
