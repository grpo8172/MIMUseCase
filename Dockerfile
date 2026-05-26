FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1             PYTHONUNBUFFERED=1             PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update             && apt-get install -y --no-install-recommends                 ca-certificates                 curl             && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip             && pip install -r /app/requirements.txt

COPY mim_pipeline_inspector.py /app/mim_pipeline_inspector.py
COPY app /app/app

RUN useradd --create-home --shell /bin/bash appuser             && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "/app/mim_pipeline_inspector.py"]
CMD ["--help"]
