#!/bin/bash
# Conduit – SessionStart hook
# Installs Python and Node.js dependencies for the backend and frontend.
# Only runs in remote (Claude Code on the web) environments.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO="$CLAUDE_PROJECT_DIR"
BACKEND="$REPO/conduit/backend"
FRONTEND="$REPO/conduit/frontend"

# ── PostgreSQL ────────────────────────────────────────────────────────────────
echo "==> Starting PostgreSQL..."
pg_ctlcluster 16 main start 2>/dev/null || true
# Wait for it to accept connections
for i in $(seq 1 10); do
  pg_isready -U postgres -q && break
  sleep 1
done

# Create DB user and database idempotently
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='conduit'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER conduit WITH PASSWORD 'conduit';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='conduit'" | grep -q 1 || \
  sudo -u postgres createdb -O postgres conduit
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE conduit TO conduit;" 2>/dev/null || true
sudo -u postgres psql conduit -c "GRANT ALL ON SCHEMA public TO conduit;" 2>/dev/null || true

# ── Python venv + backend deps ────────────────────────────────────────────────
echo "==> Installing Python dependencies..."
if [ ! -d "$BACKEND/.venv" ]; then
  python3 -m venv "$BACKEND/.venv"
fi
"$BACKEND/.venv/bin/pip" install --quiet --upgrade pip
"$BACKEND/.venv/bin/pip" install --quiet -r "$BACKEND/requirements-dev.txt"

# ── Alembic migrations ────────────────────────────────────────────────────────
echo "==> Running database migrations..."
cd "$BACKEND"
DATABASE_URL="postgresql+asyncpg://conduit:conduit@localhost:5432/conduit" \
ENCRYPTION_KEY="dev-only-32-byte-key-replace-me!" \
ENVIRONMENT=development \
  PYTHONPATH=. .venv/bin/alembic upgrade head

# Persist env vars for the session
cat >> "$CLAUDE_ENV_FILE" <<'ENVEOF'
export PYTHONPATH="."
export DATABASE_URL="postgresql+asyncpg://conduit:conduit@localhost:5432/conduit"
export ENCRYPTION_KEY="dev-only-32-byte-key-replace-me!"
export ENVIRONMENT=development
export DEBUG=true
ENVEOF

# ── Node / frontend deps ──────────────────────────────────────────────────────
echo "==> Installing frontend dependencies..."
cd "$FRONTEND"
npm install --prefer-offline --no-audit --no-fund 2>/dev/null

echo "==> Session start hook complete."
