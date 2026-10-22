"""Testes unitarios para totp_service (RFC 6238 TOTP e Backup Codes)."""

import time
from app.services.totp_service import (
    compute_totp,
    generate_backup_codes,
    generate_qr_code_data_uri,
    generate_totp_secret,
    get_totp_uri,
    serialize_backup_codes,
    verify_and_consume_backup_code,
    verify_totp,
)


def test_generate_totp_secret_format():
    secret = generate_totp_secret()
    assert isinstance(secret, str)
    assert len(secret) == 32
    # Base32 characters: A-Z, 2-7
    for char in secret:
        assert char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def test_compute_and_verify_totp_success():
    secret = generate_totp_secret()
    code = compute_totp(secret)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_totp(secret, code) is True


def test_verify_totp_invalid_code():
    secret = generate_totp_secret()
    assert verify_totp(secret, "invalid") is False
    assert verify_totp(secret, "123") is False


def test_verify_totp_tolerance_window():
    secret = generate_totp_secret()
    current_step = int(time.time()) // 30
    prev_code = compute_totp(secret, time_step=current_step - 1)
    next_code = compute_totp(secret, time_step=current_step + 1)
    far_code = compute_totp(secret, time_step=current_step - 5)

    assert verify_totp(secret, prev_code, window=1) is True
    assert verify_totp(secret, next_code, window=1) is True
    assert verify_totp(secret, far_code, window=1) is False


def test_backup_codes_generation_and_consumption():
    codes = generate_backup_codes(count=8)
    assert len(codes) == 8
    assert len(codes[0]) == 8

    serialized = serialize_backup_codes(codes)
    first_code = codes[0]

    # Consome primeiro codigo
    valid, updated_json = verify_and_consume_backup_code(
        serialized, first_code
    )
    assert valid is True
    assert updated_json is not None

    # Tenta reutilizar o mesmo codigo — deve falhar
    reused, _ = verify_and_consume_backup_code(updated_json, first_code)
    assert reused is False

    # Codigo inexistente deve falhar
    invalid, _ = verify_and_consume_backup_code(updated_json, "deadbeef")
    assert invalid is False


def test_totp_uri_generation():
    secret = "JBSWY3DPEHPK3PXP"
    email = "investidor@exemplo.com"
    uri = get_totp_uri(secret, email, issuer="SGI v2")
    expected_prefix = "otpauth://totp/SGI%20v2%3Ainvestidor%40exemplo.com?"
    assert uri.startswith(expected_prefix)
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=SGI+v2" in uri


def test_generate_qr_code_data_uri():
    uri = get_totp_uri("JBSWY3DPEHPK3PXP", "test@sgi.com")
    qr_data = generate_qr_code_data_uri(uri)
    assert qr_data.startswith("data:image/svg+xml;base64,")
    assert len(qr_data) > 100
