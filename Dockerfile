# KaushalSetu API.
#
# Multi-stage: dependencies are installed into a venv in the builder and only that venv
# is copied into the runtime image, so build toolchains never reach the final layer.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied alone so the dependency layer stays cached until requirements change.
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# curl is used by the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 kaushal

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# backend/main.py resolves imports relative to the project root, so the package is
# copied in as backend/ and the app is launched as backend.main:app from /app.
COPY --chown=kaushal:kaushal backend ./backend

# Never run as root: this process reaches the internet holding the service-role key.
USER kaushal

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Bind to $PORT when the platform sets one (Render and most PaaS do), 8000 otherwise.
# `exec` keeps uvicorn as PID 1 so SIGTERM reaches it and shutdown is prompt.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
