#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "[oci-vm-baseline] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-vm-baseline] OK: $1"
}

[ "$(id -u)" -ne 0 ] || fail "run as the ubuntu user, not root"

arch="$(uname -m)"
[ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ] || fail "expected ARM64 host, got $arch"
ok "host architecture is ARM64"

cloud_init_status="$(cloud-init status 2>/dev/null || true)"
printf '%s\n' "$cloud_init_status" | grep -q "status: done" \
  || fail "cloud-init status is unexpected: $cloud_init_status"
ok "cloud-init is done"

docker --version >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not installed"
ok "docker and compose plugin are installed"

systemctl is-active --quiet docker || fail "docker service is not active"
ok "docker service is active"

[ -d /opt/sgi-v2 ] || fail "/opt/sgi-v2 does not exist"
owner="$(stat -c '%U:%G' /opt/sgi-v2)"
[ "$owner" = "ubuntu:ubuntu" ] || fail "/opt/sgi-v2 owner must be ubuntu:ubuntu, got $owner"
ok "/opt/sgi-v2 exists and is owned by ubuntu"

ufw_status="$(sudo ufw status verbose)"
printf '%s\n' "$ufw_status" | grep -q "Status: active" || fail "ufw is not active"
printf '%s\n' "$ufw_status" | grep -q "Default: deny (incoming)" || fail "ufw incoming default is not deny"
printf '%s\n' "$ufw_status" | grep -q "allow (outgoing)" || fail "ufw outgoing default is not allow"
ok "ufw defaults are safe"

root_used_pct="$(df -P / | awk 'NR == 2 { gsub("%", "", $5); print $5 }')"
[ "$root_used_pct" -lt 80 ] || fail "root filesystem is already ${root_used_pct}% used"
ok "root filesystem has deployment headroom"

if command -v ss >/dev/null 2>&1; then
  listening="$(ss -ltnH || true)"
  if printf '%s\n' "$listening" | awk '{ print $4 }' | grep -E ':(80|443|8000|5432|6379)$' >/dev/null; then
    fail "unexpected public app/data listener found before deployment"
  fi
  ok "no pre-deploy app/data TCP listeners found"
fi

printf '%s\n' "[oci-vm-baseline] baseline check passed"
