# Multi-stage: dependencies are installed into a venv in the builder, then the venv
# alone is copied into the runtime image. Build toolchains never reach the final layer.
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app


# psycopg[binary] ships wheels, so no compiler is needed for the current requirements.
# build-essential is here because a future dependency without a wheel would otherwise
# fail the build with a confusing error.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied on its own so the dependency layer is cached until requirements change.
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# curl is used by the compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 ibolt

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=ibolt:ibolt backend ./backend
COPY --chown=ibolt:ibolt pytest.ini ./

# Never run as root: this process talks to the internet and holds the service-role key.
USER ibolt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Bind to $PORT when the platform sets one (Render and most PaaS do), and fall back to
# 8000 for local compose. `exec` hands PID 1 to uvicorn so SIGTERM reaches it and the
# container shuts down promptly instead of being killed after the grace period.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
