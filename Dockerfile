FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Base packages plus Google Cloud CLI repository.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor \
        -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        google-cloud-cli \
        kubectl \
        google-cloud-cli-gke-gcloud-auth-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY requirements-ansible.yml /app/requirements-ansible.yml

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt \
    && ansible-galaxy collection install \
        -r /app/requirements-ansible.yml \
        -p /usr/share/ansible/collections

COPY mim_pipeline_inspector.py /app/mim_pipeline_inspector.py
COPY app /app/app
COPY scripts /app/scripts
COPY playbooks /app/playbooks
COPY inventories /app/inventories

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["sh", "-c", "python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]