"""Servico de Autenticacao de Dois Fatores (MFA / 2FA) via RFC 6238 TOTP.

Implementacao em biblioteca padrao do Python (hmac, hashlib, base64, secrets)
sem dependencias externas, compativel com Google Authenticator, Authy,
Bitwarden e 1Password em computadores desktop e celulares.
"""

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
import urllib.parse
from typing import Optional


def generate_totp_secret() -> str:
    """Gera um segredo TOTP de 160 bits codificado em Base32."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")


def generate_backup_codes(count: int = 8) -> list[str]:
    """Gera codigos de recuperacao descartaveis de 8 caracteres."""
    return [secrets.token_hex(4) for _ in range(count)]


def get_totp_uri(secret: str, email: str, issuer: str = "SGI v2") -> str:
    """Gera a URI padrao otpauth:// compativel com apps de autenticacao."""
    label = f"{issuer}:{email}"
    params = {
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": "6",
        "period": "30",
    }
    query = urllib.parse.urlencode(params)
    return f"otpauth://totp/{urllib.parse.quote(label)}?{query}"


def compute_totp(
    secret: str,
    time_step: Optional[int] = None,
    interval: int = 30,
    digits: int = 6,
) -> str:
    """Calcula o codigo TOTP para o passo de tempo informado (RFC 6238)."""
    if time_step is None:
        time_step = int(time.time()) // interval

    # Normaliza e decodifica base32
    secret_clean = secret.strip().replace(" ", "").upper()
    # Adiciona padding caso necessario
    missing_padding = len(secret_clean) % 8
    if missing_padding:
        secret_clean += "=" * (8 - missing_padding)

    key = base64.b32decode(secret_clean, casefold=True)
    msg = struct.pack(">Q", time_step)
    digest = hmac.new(key, msg, hashlib.sha1).digest()

    offset = digest[-1] & 0x0F
    code_int = (
        struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    )
    otp = code_int % (10 ** digits)
    return f"{otp:0{digits}d}"


def verify_totp(
    secret: str,
    code: str,
    window: int = 1,
    interval: int = 30,
) -> bool:
    """Valida se o codigo de 6 digitos confere dentro da janela."""
    clean_code = code.strip().replace(" ", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    current_step = int(time.time()) // interval
    for offset in range(-window, window + 1):
        step = current_step + offset
        expected = compute_totp(secret, time_step=step, interval=interval)
        if hmac.compare_digest(clean_code, expected):
            return True
    return False


def hash_backup_code(code: str) -> str:
    """Hash SHA-256 para armazenamento seguro de codigo de backup."""
    clean = code.strip().lower()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def serialize_backup_codes(codes: list[str]) -> str:
    """Serializa codigos em formato JSON contendo seus hashes."""
    hashes = [hash_backup_code(c) for c in codes]
    return json.dumps(hashes)


def verify_and_consume_backup_code(
    stored_json: Optional[str],
    code: str,
) -> tuple[bool, Optional[str]]:
    """Verifica um codigo de recuperacao e o consome caso valido.

    Retorna (True, novo_json_atualizado) se valido, ou (False, stored_json).
    """
    if not stored_json:
        return False, stored_json

    try:
        hashes = json.loads(stored_json)
        if not isinstance(hashes, list):
            return False, stored_json
    except Exception:
        return False, stored_json

    code_hash = hash_backup_code(code)
    for i, h in enumerate(hashes):
        if hmac.compare_digest(h, code_hash):
            updated_hashes = hashes[:i] + hashes[i + 1 :]
            return True, json.dumps(updated_hashes)

    return False, stored_json
