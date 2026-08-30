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

# ── WeasyPrint system dependencies ───────────────
# WeasyPrint requires GObject/Pango/Cairo at the OS level.
# These are not included in python:slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Install dependencies (own layer for cache) ─
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────
COPY . .

# ── Non-root user for security ────────────────
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    # Give appuser a writable font cache directory (required by WeasyPrint/Fontconfig)
    && mkdir -p /home/appuser/.cache/fontconfig \
    && chown -R appuser:appgroup /home/appuser
USER appuser

# Set font cache dir explicitly so Fontconfig never complains
ENV XDG_CACHE_HOME=/home/appuser/.cache

# ── Expose & run ─────────────────────────────
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]