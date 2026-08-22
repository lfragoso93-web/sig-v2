#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "[oci-lab-e2micro-baseline] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-lab-e2micro-baseline] OK: $1"
}

[ "$(id -u)" -ne 0 ] || fail "run as the ubuntu user, not root"

machine_arch="$(uname -m)"
[ "$machine_arch" = "x86_64" ] || fail "expected x86_64 E2 Micro host, got $machine_arch"
ok "host architecture is x86_64"

package_arch="$(dpkg --print-architecture)"
[ "$package_arch" = "amd64" ] || fail "expected apt architecture amd64, got $package_arch"
ok "apt architecture is amd64"

cloud_init_status="$(cloud-init status 2>/dev/null || true)"
printf '%s\n' "$cloud_init_status" | grep -q "status: done" \
  || fail "cloud-init status is unexpected: $cloud_init_status"
ok "cloud-init is done"

docker --version >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not installed"
systemctl is-active --quiet docker || fail "docker service is not active"
ok "docker and compose are ready"

[ -d /opt/sgi-v2 ] || fail "/opt/sgi-v2 does not exist"
owner="$(stat -c '%U:%G' /opt/sgi-v2)"
[ "$owner" = "ubuntu:ubuntu" ] || fail "/opt/sgi-v2 owner must be ubuntu:ubuntu, got $owner"
ok "/opt/sgi-v2 exists and is owned by ubuntu"

ufw_status="$(sudo ufw status verbose)"
printf '%s\n' "$ufw_status" | grep -q "Status: active" || fail "ufw is not active"
printf '%s\n' "$ufw_status" | grep -q "Default: deny (incoming)" || fail "ufw incoming default is not deny"
printf '%s\n' "$ufw_status" | grep -q "allow (outgoing)" || fail "ufw outgoing default is not allow"
ok "ufw defaults are safe"

memory_mb="$(awk '/MemTotal/ { printf "%d", $2 / 1024 }' /proc/meminfo)"
[ "$memory_mb" -le 1400 ] || fail "expected constrained E2 Micro memory, got ${memory_mb} MB"
ok "memory profile is constrained lab class"

root_used_pct="$(df -P / | awk 'NR == 2 { gsub("%", "", $5); print $5 }')"
[ "$root_used_pct" -lt 80 ] || fail "root filesystem is already ${root_used_pct}% used"
ok "root filesystem has lab headroom"

printf '%s\n' "[oci-lab-e2micro-baseline] baseline check passed"

