#!/usr/bin/env bash
set -Eeuo pipefail

# Local-first Iteration-1 demo launcher.
# Docker is used only for Postgres and Redis; API, worker, seed, and Streamlit
# run from the local uv environment for fast development cycles.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8888}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"
SEED_YEARS="${SEED_YEARS:-2}"
SEED_SYMBOLS="${SEED_SYMBOLS:-^NSEI RELIANCE.NS}"
FULL_SEED="${FULL_SEED:-0}"
STOP_INFRA_ON_EXIT="${STOP_INFRA_ON_EXIT:-1}"
LOG_DIR="${LOG_DIR:-/tmp/indian-portfolio-intelligence}"

mkdir -p "$LOG_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://ipu:ipu@localhost:5432/ipu}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export PARQUET_DIR="${PARQUET_DIR:-$ROOT_DIR/data/parquet}"
export API_URL="${API_URL:-http://localhost:${API_PORT}}"

api_pid=""
worker_pid=""

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    [[ -n "$worker_pid" ]] && kill "$worker_pid" 2>/dev/null || true
    [[ -n "$api_pid" ]] && kill "$api_pid" 2>/dev/null || true
    if [[ "$STOP_INFRA_ON_EXIT" == "1" ]]; then
        docker compose stop postgres redis >/dev/null 2>&1 || true
    fi
    echo "Demo stopped. Logs: $LOG_DIR"
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

wait_for() {
    local description=$1
    local command=$2
    for _ in {1..30}; do
        if eval "$command" >/dev/null 2>&1; then
            echo "$description ready"
            return 0
        fi
        sleep 1
    done
    echo "$description did not become ready" >&2
    return 1
}

echo "Starting Postgres and Redis..."
docker compose up -d postgres redis >/dev/null
wait_for "Postgres" 'docker compose exec -T postgres pg_isready -U ipu -d ipu'
wait_for "Redis" 'docker compose exec -T redis redis-cli ping'

echo "Starting API on http://${API_HOST}:${API_PORT}..."
uv run uvicorn app.api.main:app --host "$API_HOST" --port "$API_PORT" \
    >"$LOG_DIR/api.log" 2>&1 &
api_pid=$!
wait_for "API" "curl --fail --silent http://${API_HOST}:${API_PORT}/health"

echo "Starting Celery worker..."
uv run celery -A app.worker:celery_app worker --loglevel=warning \
    >"$LOG_DIR/worker.log" 2>&1 &
worker_pid=$!
sleep 2
if ! kill -0 "$worker_pid" 2>/dev/null; then
    echo "Celery worker exited. See $LOG_DIR/worker.log" >&2
    exit 1
fi

if [[ "$FULL_SEED" == "1" ]]; then
    echo "Seeding full NIFTY-50 universe (this can take several minutes)..."
    uv run python -m scripts.seed_universe
else
    read -r -a symbols <<< "$SEED_SYMBOLS"
    echo "Seeding demo symbols: ${symbols[*]} (${SEED_YEARS} years)..."
    uv run python -m scripts.seed_universe \
        --symbols "${symbols[@]}" --years "$SEED_YEARS"
fi

echo "Starting Streamlit on http://localhost:${FRONTEND_PORT}..."
echo "API docs: http://localhost:${API_PORT}/docs"
echo "Press Ctrl-C to stop demo."
API_URL="http://${API_HOST}:${API_PORT}" \
    uv run streamlit run frontend/streamlit/app.py \
    --server.address 0.0.0.0 --server.port "$FRONTEND_PORT"
