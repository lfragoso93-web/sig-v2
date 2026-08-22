#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "[oci-lab-image-pull] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-lab-image-pull] OK: $1"
}

[ "$(id -u)" -ne 0 ] || fail "run as the ubuntu user, not root"
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker info >/dev/null 2>&1 || fail "docker daemon is not reachable by this user"

images="
postgres:16-alpine
redis:7-alpine
cloudflare/cloudflared:latest
"

for image in $images; do
  docker pull "$image"
  docker image inspect "$image" >/dev/null
  ok "pulled $image"
done

docker image rm hello-world:latest >/dev/null 2>&1 || true

printf '%s\n' "[oci-lab-image-pull] image pull check passed"
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | sed -n '1,20p'

