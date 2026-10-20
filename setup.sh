#!/usr/bin/env bash
set -Eeuo pipefail

# One-command setup for macOS and Linux. Docker Engine and Compose must already
# be installed and running; Compose downloads the app image and Ollama models.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

fail() {
  printf '\nSetup failed: %s\n' "$1" >&2
  printf 'Check the Docker services with: docker compose ps -a\n' >&2
  printf 'View model setup logs with: docker compose logs ollama-models\n' >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is not installed. Install Docker Desktop (macOS) or Docker Engine and the Compose plugin (Linux), then run this script again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose is unavailable. Install a current Docker Desktop or Docker Compose plugin."
docker info >/dev/null 2>&1 || fail "Docker Engine is not running. Start Docker Desktop or the Docker service, wait until it is ready, and retry."

printf 'Starting the perfume store and local Ollama models.\n'
printf 'On first setup, Docker images and missing models are downloaded; internet is required.\n\n'

if ! docker compose up --build -d; then
  docker compose ps -a || true
  docker compose logs --tail 80 ollama ollama-models web || true
  fail "Docker Compose could not complete startup. See the service status and logs above."
fi

# The model setup is a one-shot container and can take many minutes on a new
# computer. Wait for it explicitly before checking the dependent web service.
MODEL_CONTAINER=""
until [[ -n "$MODEL_CONTAINER" ]]; do
  MODEL_CONTAINER="$(docker compose ps -aq ollama-models 2>/dev/null | head -n 1)"
  [[ -n "$MODEL_CONTAINER" ]] || sleep 2
done

ELAPSED=0
while true; do
  MODEL_STATE="$(docker inspect --format '{{.State.Status}}|{{.State.ExitCode}}' "$MODEL_CONTAINER")" \
    || fail "Could not read the Ollama model setup status."
  case "$MODEL_STATE" in
    exited\|0) break ;;
    exited\|*) docker compose logs --tail 80 ollama-models || true; fail "Ollama model download/setup failed." ;;
    dead\|*) docker compose logs --tail 80 ollama-models || true; fail "Ollama model setup container stopped unexpectedly." ;;
  esac
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  if (( ELAPSED >= 60 )); then
    printf 'Still preparing the models (%s seconds elapsed)...\n' "$ELAPSED"
    ELAPSED=0
  fi
done

RUNNING_SERVICES="$(docker compose ps --status running --services 2>/dev/null || true)"
if ! printf '%s\n' "$RUNNING_SERVICES" | grep -qx 'web'; then
  docker compose ps -a || true
  docker compose logs --tail 80 ollama ollama-models web || true
  fail "The web service is not running. Model download may have failed or still be in progress."
fi

printf '\nSetup complete.\n'
printf 'Store:       http://localhost:8000/en/\n'
printf 'Arabic page: http://localhost:8000/ar/\n\n'
printf 'Installed Ollama models:\n'
docker compose exec -T ollama ollama list || true

if command -v open >/dev/null 2>&1; then
  open 'http://localhost:8000/en/' >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open 'http://localhost:8000/en/' >/dev/null 2>&1 || true
fi
