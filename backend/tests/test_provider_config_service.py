"""Testes para gestão dinâmica de provedores de mercado (Issue #127)."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderId,
    decrypt_secret,
    encrypt_secret,
    mask_secret,
)
from app.core.provider_status import ProviderStatus
from app.models.audit_log import AuditLog
from app.models.provider_configuration import ProviderConfiguration
from app.models.user import User, UserRole
from app.schemas.provider_config import ProviderConfigUpdate
from app.services.provider_config_service import ProviderConfigService


@pytest.mark.asyncio
async def test_secret_encryption_and_masking() -> None:
    """Valida criptografia bidirecional Fernet e mascaramento de chaves."""
    raw = "brapi_secret_token_12345"
    encrypted = encrypt_secret(raw)
    assert encrypted is not None
    assert encrypted != raw

    decrypted = decrypt_secret(encrypted)
    assert decrypted == raw

    masked = mask_secret(raw)
    assert masked is not None
    assert "bra" in masked
    assert "345" in masked
    assert "****" in masked
    assert raw not in masked

    assert mask_secret(None) is None
    assert mask_secret("") is None
    assert mask_secret("1234") == "****"


@pytest.mark.asyncio
async def test_list_providers_returns_all_registered(db: AsyncSession) -> None:
    """Provedores registrados listados com campos seguros."""
    providers = await ProviderConfigService.list_providers(db)
    assert len(providers) == len(PROVIDER_REGISTRY)

    ids = {p.provider_id for p in providers}
    assert ProviderId.BRAPI.value in ids
    assert ProviderId.B3_COTAHIST.value in ids
    assert ProviderId.BACEN_SGS.value in ids
    assert ProviderId.TESOURO_TRANSPARENTE.value in ids

    for p in providers:
        assert p.display_name
        assert len(p.capabilities) > 0
        if p.api_key_masked:
            assert "****" in p.api_key_masked


@pytest.mark.asyncio
async def test_get_effective_provider_config_fallback(
    db: AsyncSession,
) -> None:
    """Resolução com fallback para padrões estáticos quando sem banco."""
    effective = await ProviderConfigService.get_effective_provider_config(
        ProviderId.BACEN_SGS.value, db
    )
    assert effective.provider_id == ProviderId.BACEN_SGS.value
    assert effective.is_enabled is True
    assert effective.priority == 1
    assert effective.base_url == "https://api.bcb.gov.br"
    assert effective.timeout_seconds == 15
    assert effective.is_source_db is False


@pytest.mark.asyncio
async def test_update_provider_config_persists_encrypted_and_audited(
    db: AsyncSession,
) -> None:
    """Valida persistência com chave encriptada e log de auditoria."""
    user = User(
        name="Admin Test",
        email="superadmin_test@sgi.local",
        hashed_password="hash",
        role=UserRole.superadmin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    update_dto = ProviderConfigUpdate(
        is_enabled=True,
        priority=3,
        base_url="https://custom.brapi.dev",
        timeout_seconds=25,
        rate_limit_per_minute=500,
        new_api_key="my_new_secret_token_xyz",
    )

    resp = await ProviderConfigService.update_provider_config(
        provider_id=ProviderId.BRAPI.value,
        data=update_dto,
        user_id=user.id,
        db=db,
        ip_address="192.168.1.100",
        user_agent="Pytest-Client",
    )

    assert resp.provider_id == ProviderId.BRAPI.value
    assert resp.priority == 3
    assert resp.base_url == "https://custom.brapi.dev"
    assert resp.timeout_seconds == 25
    assert resp.has_api_key_configured is True
    assert resp.api_key_masked is not None
    assert "my_new_secret_token_xyz" not in resp.api_key_masked

    # Verifica no banco: chave deve estar criptografada
    stmt = select(ProviderConfiguration).where(
        ProviderConfiguration.provider_id == ProviderId.BRAPI.value
    )
    result = await db.execute(stmt)
    db_cfg = result.scalar_one()
    assert db_cfg.api_key_encrypted is not None
    assert db_cfg.api_key_encrypted != "my_new_secret_token_xyz"
    assert (
        decrypt_secret(db_cfg.api_key_encrypted) == "my_new_secret_token_xyz"
    )

    # Verifica log de auditoria
    audit_stmt = select(AuditLog).where(
        AuditLog.resource_type == "PROVIDER_CONFIG",
        AuditLog.action == "UPDATE",
    )
    audit_res = await db.execute(audit_stmt)
    audit_log = audit_res.scalar_one()
    assert audit_log.user_id == user.id
    assert audit_log.status == "SUCCESS"
    assert audit_log.ip_address == "192.168.1.100"


@pytest.mark.asyncio
async def test_reset_provider_to_default(db: AsyncSession) -> None:
    """Verifica remoção da customização e restauração do fallback."""
    user = User(
        name="Admin Test 2",
        email="superadmin2_test@sgi.local",
        hashed_password="hash",
        role=UserRole.superadmin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await ProviderConfigService.update_provider_config(
        provider_id=ProviderId.ALPHA_VANTAGE.value,
        data=ProviderConfigUpdate(priority=88, timeout_seconds=45),
        user_id=user.id,
        db=db,
    )

    reset_resp = await ProviderConfigService.reset_provider_to_default(
        provider_id=ProviderId.ALPHA_VANTAGE.value,
        user_id=user.id,
        db=db,
    )

    assert reset_resp.is_customized is False
    assert reset_resp.priority == 15
    assert reset_resp.timeout_seconds == 20


@pytest.mark.asyncio
async def test_b3_cotahist_connectivity_probe(db: AsyncSession) -> None:
    """Valida probe do provedor B3 COTAHIST."""
    test_result = await ProviderConfigService.test_provider_connectivity(
        ProviderId.B3_COTAHIST.value, db
    )
    assert test_result.provider_id == ProviderId.B3_COTAHIST.value
    assert test_result.success is True
    assert test_result.status == ProviderStatus.OK.value
    assert test_result.latency_ms >= 0
    assert "COTAHIST" in test_result.message
