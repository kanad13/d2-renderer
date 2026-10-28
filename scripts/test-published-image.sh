#!/usr/bin/env bash
# Pulls the published container image from GitHub Container Registry, runs it locally,
# and executes the integration test suite and behavior probe against it.
set -euo pipefail

IMAGE="${1:-${IMAGE:-ghcr.io/kanad13/d2-renderer:latest}}"
CONTAINER_NAME="d2-published-check"
PORT="${PORT:-8080}"

echo "==> Pulling published image: ${IMAGE}"
docker pull "${IMAGE}"

cleanup() {
  echo "==> Cleaning up container: ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Starting container: ${CONTAINER_NAME} on port ${PORT}"
docker run -d --name "${CONTAINER_NAME}" -p "${PORT}:8080" --add-host=host.docker.internal:host-gateway "${IMAGE}"

echo "==> Waiting for server health check"
for i in {1..20}; do
  if curl -s "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -q "OK"; then
    echo "==> Server is healthy"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "==> Timed out waiting for server"
    docker logs "${CONTAINER_NAME}"
    exit 1
  fi
  sleep 0.5
done

echo "==> Running integration tests"
TEST_TARGET_URL="http://127.0.0.1:${PORT}" python3 -m unittest discover -s tests -v

echo "==> Running behavior probe"
python3 scripts/probe-behavior.py "http://127.0.0.1:${PORT}"

echo "==> Published image test completed successfully"
