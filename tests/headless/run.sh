#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
render_node=${HEADLESS_RENDER_NODE:-/dev/dri/renderD128}
if [[ ! "$render_node" =~ ^/dev/dri/renderD[0-9]+$ ]] || [[ ! -c "$render_node" ]] || [[ ! -r "$render_node" || ! -w "$render_node" ]]; then
    echo "FAIL: readable/writable DRM render node required: $render_node" >&2
    exit 1
fi
command -v docker >/dev/null || { echo "FAIL: Docker is required" >&2; exit 1; }
mkdir -p "$repo/tests/headless/artifacts"
artifacts=$(mktemp -d "$repo/tests/headless/artifacts/run-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
echo "Artifacts: $artifacts"
container="hypr-headless-test-$(id -u)-${artifacts##*/}"
cleanup() {
    docker stop --time 12 "$container" >/dev/null 2>&1 || true
    docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
timeout 600 docker build --iidfile "$artifacts/image-id.txt" "$repo/tests/headless" >"$artifacts/build.log" 2>&1 || {
    tail -60 "$artifacts/build.log" >&2; exit 1;
}
image=$(<"$artifacts/image-id.txt")
docker image inspect "$image" >"$artifacts/image.json"
docker version >"$artifacts/docker-version.txt"
# Private namespaces, no networking or host IPC; only render node and these mounts.
docker create --init --name "$container" --network none \
    --cap-drop ALL --security-opt no-new-privileges \
    --user "$(id -u):$(id -g)" --group-add "$(stat -c %g "$render_node")" \
    --device "$render_node:$render_node" \
    --mount "type=bind,src=$repo,dst=/source,readonly" \
    --mount "type=bind,src=$artifacts,dst=/artifacts" \
    --env "HEADLESS_RENDER_NODE=$render_node" \
    --env "HEADLESS_TEST_FILE=${HEADLESS_TEST_FILE:-tests/headless/test_runtime.py}" \
    "$image" >"$artifacts/container-id.txt"
docker inspect "$container" >"$artifacts/container.json"
docker start --attach "$container" >"$artifacts/session.log" 2>&1 &
runner=$!
# Bound the whole runtime even if readiness or a subprocess regresses.
deadline=$((SECONDS + 180))
while kill -0 "$runner" 2>/dev/null; do
    if (( SECONDS >= deadline )); then
        echo "FAIL: container runtime exceeded 180 seconds" >&2
        cleanup
        wait "$runner" || true
        tail -80 "$artifacts/session.log" >&2
        exit 1
    fi
    sleep 1
done
status=0
wait "$runner" || status=$?
container_status=$(docker inspect --format '{{.State.ExitCode}}' "$container")
docker inspect "$container" >"$artifacts/container-final.json"
if (( status == 0 )); then status=$container_status; fi
cat "$artifacts/session.log"
echo "Artifacts: $artifacts"
exit "$status"
