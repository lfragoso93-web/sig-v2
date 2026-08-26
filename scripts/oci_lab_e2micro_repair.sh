#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "[oci-lab-e2micro-repair] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-lab-e2micro-repair] OK: $1"
}

[ "$(id -u)" -eq 0 ] || fail "run with sudo"

arch="$(dpkg --print-architecture)"
[ "$arch" = "amd64" ] || fail "expected E2 Micro amd64 host, got $arch"
ok "host package architecture is amd64"

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
printf '%s\n' "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
ok "docker apt source uses arch=${arch}"

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
ok "docker installed and enabled"

install -d -o ubuntu -g ubuntu -m 0755 /opt/sgi-v2
usermod -aG docker ubuntu
ok "/opt/sgi-v2 and docker group are configured"

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
ok "ufw baseline applied with SSH allowed for lab access"

docker --version
docker compose version

printf '%s\n' "[oci-lab-e2micro-repair] repair completed; reconnect SSH for docker group membership to apply"
