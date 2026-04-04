#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose.support-services.yaml"
DEFAULT_ENV_FILE="$ROOT_DIR/.env.local"
ENV_FILE="${IRON_COUNCIL_ENV_FILE:-$DEFAULT_ENV_FILE}"
SERVER_HOST="${IRON_COUNCIL_SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${IRON_COUNCIL_SERVER_PORT:-8000}"
SERVER_RELOAD="${IRON_COUNCIL_SERVER_RELOAD:-false}"
CLIENT_HOST="${IRON_COUNCIL_CLIENT_HOST:-127.0.0.1}"
CLIENT_PORT="${IRON_COUNCIL_CLIENT_PORT:-3000}"
MATCH_REGISTRY_BACKEND="${IRON_COUNCIL_MATCH_REGISTRY_BACKEND:-db}"

usage() {
  cat <<'EOF'
Iron Council runtime control

Usage:
  ./scripts/runtime-control.sh doctor
  ./scripts/runtime-control.sh support-up
  ./scripts/runtime-control.sh support-down
  ./scripts/runtime-control.sh db-setup
  ./scripts/runtime-control.sh db-reset
  ./scripts/runtime-control.sh server
  ./scripts/runtime-control.sh client-install
  ./scripts/runtime-control.sh client-dev
  ./scripts/runtime-control.sh client-build
  ./scripts/runtime-control.sh client-start

Environment knobs:
  IRON_COUNCIL_ENV_FILE        Server env file path (default: .env.local)
  IRON_COUNCIL_MATCH_REGISTRY_BACKEND  Server backend (default: db)
  IRON_COUNCIL_SERVER_HOST     Uvicorn host (default: 127.0.0.1)
  IRON_COUNCIL_SERVER_PORT     Uvicorn port (default: 8000)
  IRON_COUNCIL_SERVER_RELOAD   true/false for uvicorn --reload (default: false)
  IRON_COUNCIL_CLIENT_HOST     Next.js host (default: 127.0.0.1)
  IRON_COUNCIL_CLIENT_PORT     Next.js port (default: 3000)
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

docker_compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

run_uv() {
  (cd "$ROOT_DIR" && uv "$@")
}

run_client() {
  (cd "$ROOT_DIR/client" && "$@")
}

cmd_doctor() {
  require_cmd uv
  require_cmd npm
  require_cmd docker

  if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "Missing compose file: $COMPOSE_FILE" >&2
    exit 1
  fi

  if [[ "$MATCH_REGISTRY_BACKEND" != "db" && "$MATCH_REGISTRY_BACKEND" != "memory" ]]; then
    echo "Unsupported IRON_COUNCIL_MATCH_REGISTRY_BACKEND: $MATCH_REGISTRY_BACKEND" >&2
    exit 1
  fi

  cat <<EOF
Runtime doctor summary
- repo: $ROOT_DIR
- compose file: $COMPOSE_FILE
- server env file: $ENV_FILE
- server URL: http://$SERVER_HOST:$SERVER_PORT
- client URL: http://$CLIENT_HOST:$CLIENT_PORT
- match registry backend: $MATCH_REGISTRY_BACKEND
- support services command: docker compose -f compose.support-services.yaml up -d postgres
- health check: curl http://$SERVER_HOST:$SERVER_PORT/health
- runtime status check: curl http://$SERVER_HOST:$SERVER_PORT/health/runtime
EOF

  if [[ -f "$ENV_FILE" ]]; then
    echo "- env file exists: yes"
  else
    echo "- env file exists: no (copy env.local.example or point IRON_COUNCIL_ENV_FILE elsewhere)"
  fi
}

cmd_support_up() {
  require_cmd docker
  if docker_compose up --help 2>/dev/null | grep -q -- '--wait'; then
    docker_compose up -d --wait postgres
  else
    docker_compose up -d postgres
  fi
}

cmd_support_down() {
  require_cmd docker
  docker_compose down
}

cmd_db_setup() {
  require_cmd uv
  run_uv run python -m server.db.tooling setup
}

cmd_db_reset() {
  require_cmd uv
  run_uv run python -m server.db.tooling reset
}

cmd_server() {
  require_cmd uv
  local -a uvicorn_args=(run uvicorn server.main:app --host "$SERVER_HOST" --port "$SERVER_PORT")
  if [[ "$SERVER_RELOAD" == "true" ]]; then
    uvicorn_args+=(--reload)
  fi

  cd "$ROOT_DIR"
  export IRON_COUNCIL_ENV_FILE="$ENV_FILE"
  export IRON_COUNCIL_MATCH_REGISTRY_BACKEND="$MATCH_REGISTRY_BACKEND"
  exec uv "${uvicorn_args[@]}"
}

cmd_client_install() {
  require_cmd npm
  run_client npm ci
}

cmd_client_dev() {
  require_cmd npm
  cd "$ROOT_DIR/client"
  exec npm run dev -- --hostname "$CLIENT_HOST" --port "$CLIENT_PORT"
}

cmd_client_build() {
  require_cmd npm
  run_client npm run build
}

cmd_client_start() {
  require_cmd npm
  cd "$ROOT_DIR/client"
  exec npm run start -- --hostname "$CLIENT_HOST" --port "$CLIENT_PORT"
}

main() {
  local command="${1:-help}"
  case "$command" in
    help|-h|--help)
      usage
      ;;
    doctor)
      cmd_doctor
      ;;
    support-up)
      cmd_support_up
      ;;
    support-down)
      cmd_support_down
      ;;
    db-setup)
      cmd_db_setup
      ;;
    db-reset)
      cmd_db_reset
      ;;
    server)
      cmd_server
      ;;
    client-install)
      cmd_client_install
      ;;
    client-dev)
      cmd_client_dev
      ;;
    client-build)
      cmd_client_build
      ;;
    client-start)
      cmd_client_start
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
