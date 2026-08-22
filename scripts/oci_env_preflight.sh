#!/usr/bin/env sh
set -eu

ENV_FILE="${1:-.env}"

fail() {
  printf '%s\n' "[oci-env-preflight] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-env-preflight] OK: $1"
}

[ -f "$ENV_FILE" ] || fail "env file not found: $ENV_FILE"

get_value() {
  key="$1"
  value="$(sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1)"
  printf '%s' "$value"
}

require_nonempty() {
  key="$1"
  value="$(get_value "$key")"
  [ -n "$value" ] || fail "$key is empty"
}

require_not_placeholder() {
  key="$1"
  value="$(get_value "$key")"
  case "$value" in
    unknown|change-this-on-vm|replace-with-*|https://your-sgi-hostname.example|admin@your-domain.example)
      fail "$key still contains placeholder value"
      ;;
  esac
}

require_nonempty APP_COMMIT_SHA
require_not_placeholder APP_COMMIT_SHA

require_nonempty POSTGRES_PASSWORD
require_not_placeholder POSTGRES_PASSWORD
case "$(get_value POSTGRES_PASSWORD)" in
  *[!A-Za-z0-9._~-]*) fail "POSTGRES_PASSWORD must be URL-safe: use letters, numbers, dot, underscore, tilde, or hyphen" ;;
esac

require_nonempty DATABASE_URL
require_not_placeholder DATABASE_URL

require_nonempty ASYNC_DATABASE_URL
require_not_placeholder ASYNC_DATABASE_URL

postgres_password="$(get_value POSTGRES_PASSWORD)"
case "$(get_value DATABASE_URL)" in
  *":${postgres_password}@db:5432/"*) ;;
  *) fail "DATABASE_URL must use POSTGRES_PASSWORD and host db:5432" ;;
esac
case "$(get_value ASYNC_DATABASE_URL)" in
  *":${postgres_password}@db:5432/"*) ;;
  *) fail "ASYNC_DATABASE_URL must use POSTGRES_PASSWORD and host db:5432" ;;
esac

require_nonempty SECRET_KEY
require_not_placeholder SECRET_KEY
[ "$(get_value SECRET_KEY | wc -c | tr -d ' ')" -ge 32 ] || fail "SECRET_KEY must have at least 32 characters"

require_nonempty CORS_ORIGINS
require_not_placeholder CORS_ORIGINS
case "$(get_value CORS_ORIGINS)" in
  https://*) ;;
  *) fail "CORS_ORIGINS must start with https://" ;;
esac
case "$(get_value CORS_ORIGINS)" in
  *localhost*|*127.0.0.1*) fail "CORS_ORIGINS must not point to localhost in production" ;;
esac

require_nonempty SUPERADMIN_EMAIL
require_not_placeholder SUPERADMIN_EMAIL

require_nonempty SUPERADMIN_PASSWORD
require_not_placeholder SUPERADMIN_PASSWORD

require_nonempty CLOUDFLARE_TUNNEL_TOKEN

[ "$(get_value ENVIRONMENT)" = "production" ] || fail "ENVIRONMENT must be production"
[ "$(get_value APP_DEBUG)" = "false" ] || fail "APP_DEBUG must be false"
[ "$(get_value BACKEND_WORKERS)" = "1" ] || fail "BACKEND_WORKERS must remain 1 on the initial 1 OCPU VM"
[ -z "$(get_value VITE_API_URL)" ] || fail "VITE_API_URL must remain empty for nginx /api proxy"

ok "required production values are present"
ok "placeholders are not present"
ok "database URLs and CORS origin match the OCI production profile"
ok "initial OCI worker/profile values are safe"
