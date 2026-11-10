#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export BASELINE_IMAGE="hsds-baseline:$(git rev-parse HEAD)"
tmp=$(mktemp -d)
project="baseline-$$"
container="baseline-direct-$$"
compose=(docker compose -p "$project" -f "$tmp/compose.yml")
cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    docker logs "$container" || true
    "${compose[@]}" logs || true
  fi
  docker rm -f "$container" >/dev/null 2>&1 || true
  "${compose[@]}" down --volumes || true
  rm -rf "$tmp"
  exit "$status"
}
trap cleanup EXIT
# Preserve the real Compose service configuration, but isolate names/ports and
# force Compose to run the exact image already checked directly (no rebuild).
docker compose config --format json > "$tmp/source.json"
uv run --locked --extra api python - "$tmp" <<'PY'
import json
import pathlib
import sys
import os
path = pathlib.Path(sys.argv[1])
config = json.loads((path / "source.json").read_text())
config.pop("name", None)
# Resolved Compose config embeds project-prefixed network names. Let the
# isolated smoke project supply them instead of sharing the developer network.
for network in config.get("networks", {}).values():
    if not network.get("external", False):
        network.pop("name", None)
service = config["services"]["api"]
service.pop("build", None)
service.pop("container_name", None)
service["image"] = os.environ["BASELINE_IMAGE"]
service["ports"] = [{"target": 8000, "published": "0", "host_ip": "127.0.0.1", "protocol": "tcp"}]
(path / "compose.yml").write_text(json.dumps(config))
PY
docker build --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" -t "$BASELINE_IMAGE" .
smoke() {
  local id="$1" port="$2"
  for _ in $(seq 1 60); do
    if [ "$(docker inspect --format '{{.State.Health.Status}}' "$id")" = healthy ]; then
      uv run --locked --extra api python scripts/check-http.py "http://127.0.0.1:$port"
      return
    fi
    sleep 2
  done
  echo "Container did not become healthy: $id" >&2
  return 1
}
docker run -d --name "$container" -p 127.0.0.1::8000 "$BASELINE_IMAGE"
smoke "$container" "$(docker port "$container" 8000/tcp | awk -F: '{print $NF}')"
docker rm -f "$container"
"${compose[@]}" up -d --no-build
smoke "$("${compose[@]}" ps -q api)" "$("${compose[@]}" port api 8000 | awk -F: '{print $NF}')"
