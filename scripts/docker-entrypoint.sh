#!/bin/sh
# Open Notebook container entrypoint.
#
# Installs the OPT-IN heavy extraction runtimes (Docling, Crawl4AI local) when the
# operator enables them via env vars, then hands off to CMD (supervisord).
#
#   OPEN_NOTEBOOK_ENABLE_DOCLING=true   -> content-core[docling]  (Docling engine, OCR, image sources)
#   OPEN_NOTEBOOK_ENABLE_CRAWL4AI=true  -> content-core[crawl4ai] + Chromium  (local JS rendering)
#
# Design (see docs/7-DEVELOPMENT/decisions/ADR-007-optin-runtimes.md):
#   - Blocking: installs finish before api/worker/frontend start.
#   - Degrade, don't die: a failed install logs LOUDLY and boot continues; the
#     runtime is simply reported unavailable by GET /api/capabilities.
#   - Caches persist on the /app/data volume (UV_CACHE_DIR, PLAYWRIGHT_BROWSERS_PATH,
#     HF_HOME), so a second boot reinstalls from cache instead of re-downloading.
#   - The venv itself lives in the image layer (ephemeral per container), so we
#     probe the actual venv each boot and reinstall when a fresh container lacks
#     the extra. This is immune to Python-version bumps in the base image.
#
# POSIX /bin/sh (dash) compatible — no bashisms.

VENV_PY="/app/.venv/bin/python"

# Chromium's system libraries (installed via apt by `playwright install --with-deps`)
# live in the CONTAINER filesystem, which resets per container — so this marker
# lives there too (NOT on the volume), making --with-deps run once per container.
PLAYWRIGHT_DEPS_STAMP="/app/.playwright-system-deps.done"

log() { echo "[entrypoint] $*"; }

is_true() {
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
        1 | true | yes | on) return 0 ;;
        *) return 1 ;;
    esac
}

has_module() {
    "$VENV_PY" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$1') else 1)" 2>/dev/null
}

# Pin the extra to the base install's content-core version so its transitive deps
# stay compatible with what's already locked in the image.
ccore_version() {
    "$VENV_PY" -c "import importlib.metadata as m; print(m.version('content-core'))" 2>/dev/null
}

# Ensure the cache directories exist on the (possibly freshly mounted) volume.
mkdir -p "${UV_CACHE_DIR:-/app/data/.cache/uv}" \
    "${PLAYWRIGHT_BROWSERS_PATH:-/app/data/.cache/playwright}" \
    "${HF_HOME:-/app/data/.cache/huggingface}" 2>/dev/null || true

CCORE_VERSION="$(ccore_version)"

# ---------------------------------------------------------------------------
# Docling
# ---------------------------------------------------------------------------
if is_true "$OPEN_NOTEBOOK_ENABLE_DOCLING"; then
    if has_module docling; then
        log "Docling already installed; skipping."
    elif [ -z "$CCORE_VERSION" ]; then
        log "WARNING: could not determine content-core version; skipping Docling install."
    else
        log "Installing Docling (first start; this pulls a large ML stack — several hundred MB to a few GB — and can take several minutes)..."
        if uv pip install --python "$VENV_PY" "content-core[docling]==${CCORE_VERSION}"; then
            log "Docling installed. The Docling engine, OCR and image sources are now available."
        else
            log "WARNING: Docling install FAILED. Booting without it — the Docling engine, OCR and image sources will be unavailable. Fix connectivity and restart to retry."
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Crawl4AI (local). A remote server via CRAWL4AI_API_URL needs no local install.
# ---------------------------------------------------------------------------
if is_true "$OPEN_NOTEBOOK_ENABLE_CRAWL4AI"; then
    if [ -n "$CRAWL4AI_API_URL" ]; then
        log "CRAWL4AI_API_URL is set; using the remote Crawl4AI service (no local install)."
    else
        if has_module crawl4ai; then
            log "Crawl4AI package already installed."
        elif [ -z "$CCORE_VERSION" ]; then
            log "WARNING: could not determine content-core version; skipping Crawl4AI install."
        else
            log "Installing Crawl4AI local runtime (first start; also downloads a Chromium browser ~150MB)..."
            if uv pip install --python "$VENV_PY" "content-core[crawl4ai]==${CCORE_VERSION}"; then
                log "Crawl4AI package installed."
            else
                log "WARNING: Crawl4AI install FAILED. Booting without local Crawl4AI — set CRAWL4AI_API_URL to use a remote server instead."
            fi
        fi

        # Ensure the Chromium browser (persisted on the volume) and its system
        # libraries (container FS, once per container) are present.
        if has_module crawl4ai; then
            if [ -f "$PLAYWRIGHT_DEPS_STAMP" ]; then
                if "$VENV_PY" -m playwright install chromium >/dev/null 2>&1; then
                    log "Chromium browser ready."
                else
                    log "WARNING: 'playwright install chromium' failed; local Crawl4AI may not render pages."
                fi
            else
                log "Installing Chromium browser + system libraries (one-time for this container)..."
                if "$VENV_PY" -m playwright install --with-deps chromium; then
                    touch "$PLAYWRIGHT_DEPS_STAMP"
                    log "Chromium browser + system libraries ready."
                else
                    log "WARNING: 'playwright install --with-deps chromium' failed; local Crawl4AI may not render pages."
                fi
            fi
        fi
    fi
fi

log "Starting Open Notebook."
exec "$@"
