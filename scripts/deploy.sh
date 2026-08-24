#!/usr/bin/env bash
# Run on the deployment host after git pull (see .github/workflows/deploy.yml).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing in $ROOT" >&2
  echo "Copy .env.example to .env and set environment values before deploying." >&2
  exit 1
fi

if [[ -z "${API_IMAGE:-}" || -z "${WEB_IMAGE:-}" ]]; then
  echo "ERROR: API_IMAGE and WEB_IMAGE must be set." >&2
  exit 1
fi

registry_login() {
  if [[ -z "${REGISTRY_HOST:-}" ]]; then
    return 0
  fi

  if [[ "${REGISTRY_HOST}" == *".amazonaws.com" ]]; then
    if ! command -v aws >/dev/null 2>&1; then
      echo "ERROR: aws CLI is required to pull from ECR (${REGISTRY_HOST})." >&2
      exit 1
    fi
    local region="${AWS_REGION:-eu-central-1}"
    echo "==> Logging into ECR (${REGISTRY_HOST}, region=${region})"
    aws ecr get-login-password --region "${region}" \
      | docker login --username AWS --password-stdin "${REGISTRY_HOST}"
    return 0
  fi

  if [[ -n "${REGISTRY_USERNAME:-}" && -n "${REGISTRY_PASSWORD:-}" ]]; then
    echo "==> Logging into ${REGISTRY_HOST}"
    echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY_HOST}" -u "${REGISTRY_USERNAME}" --password-stdin
  fi
}

registry_login

echo "==> Pulling images"
API_IMAGE="$API_IMAGE" WEB_IMAGE="$WEB_IMAGE" docker compose -f "$COMPOSE_FILE" pull

echo "==> Starting stack ($COMPOSE_FILE)"
API_IMAGE="$API_IMAGE" WEB_IMAGE="$WEB_IMAGE" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Waiting for API and frontend health"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1/" >/dev/null 2>&1; then
    echo "API and frontend are up"
    exit 0
  fi
  sleep 2
done

echo "WARN: API/frontend health check did not pass within 60s (stack may still be starting)" >&2
docker compose -f "$COMPOSE_FILE" ps
exit 1
