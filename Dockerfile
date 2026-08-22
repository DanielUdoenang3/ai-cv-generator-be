# ─────────────────────────────────────────────
#  Stage: runtime
#  python:3.13-slim  ~50 MB vs ~1 GB (full)
# ─────────────────────────────────────────────
FROM python:3.13-slim

# ── Python runtime hygiene ───────────────────
#   Don't write .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
#   Ensure stdout/stderr are sent straight to the container log
ENV PYTHONUNBUFFERED=1
#   Keep pip quiet and deterministic
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# ── Install dependencies (own layer for cache) ─
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────
COPY . .

# ── Non-root user for security ────────────────
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser
USER appuser

# ── Expose & run ─────────────────────────────
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]