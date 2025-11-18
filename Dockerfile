FROM python:3.11-slim AS runtime

ARG UV_VERSION=0.4.20
ARG TERRAFORM_VERSION=1.9.5

ENV PATH="/root/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Install uv (dependency manager / runner)
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_VERSION="${UV_VERSION}" sh

# Install Terraform binary
RUN curl -fsSLo /tmp/terraform.zip \
        "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip \
    && terraform version

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY main.py /app/main.py

# Install Python dependencies using uv
RUN uv sync --no-dev

EXPOSE 8000

ENV SIDECAR_TERRAFORM_ROOT=/tfpjts \
    SIDECAR_LOCK_DIR=/tmp/tf_locks \
    SIDECAR_STARTUP_INIT_ENABLED=true

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

