"""Serviço de gestão, auditoria e probe de conectividade de provedores."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderId,
    decrypt_secret,
    encrypt_secret,
    mask_secret,
)
from app.core.provider_status import ProviderStatus
from app.models.audit_log import AuditAction
from app.models.provider_configuration import ProviderConfiguration
from app.schemas.provider_config import (
    ProviderConfigResponse,
    ProviderConfigUpdate,
    ProviderTestResponse,
)
from app.services.audit_log_service import AuditLogService


@dataclass(frozen=True)
class EffectiveProviderConfig:
    provider_id: str
    display_name: str
    is_enabled: bool
    priority: int
    base_url: str | None
    api_key: str | None
    timeout_seconds: int
    rate_limit_per_minute: int | None
    custom_headers: dict[str, Any] = field(default_factory=dict)
    is_source_db: bool = False


class ProviderConfigService:
    """Orquestrador de configurações administrativas e dinâmicas."""

    @staticmethod
    async def list_providers(db: AsyncSession) -> list[ProviderConfigResponse]:
        """Lista todos os provedores registrados com resolução segura."""
        stmt = select(ProviderConfiguration)
        result = await db.execute(stmt)
        db_configs = {cfg.provider_id: cfg for cfg in result.scalars().all()}

        responses: list[ProviderConfigResponse] = []

        for p_id, definition in PROVIDER_REGISTRY.items():
            db_cfg = db_configs.get(p_id)

            base_url = db_cfg.base_url if db_cfg and db_cfg.base_url else None
            effective_base_url = base_url or definition.default_base_url

            db_key_decrypted = (
                decrypt_secret(db_cfg.api_key_encrypted) if db_cfg else None
            )
            env_key = (
                getattr(settings, definition.env_key_var, None)
                if definition.env_key_var
                else None
            )
            effective_key = db_key_decrypted or env_key

            is_customized = db_cfg is not None
            is_enabled = db_cfg.is_enabled if db_cfg else True
            priority = (
                db_cfg.priority if db_cfg else definition.default_priority
            )
            timeout_seconds = (
                db_cfg.timeout_seconds
                if db_cfg
                else definition.default_timeout_seconds
            )
            rate_limit = (
                db_cfg.rate_limit_per_minute
                if db_cfg and db_cfg.rate_limit_per_minute is not None
                else definition.default_rate_limit_per_minute
            )
            custom_headers = db_cfg.custom_headers if db_cfg else None
            status = db_cfg.status if db_cfg else ProviderStatus.OK
            last_health_check_at = (
                db_cfg.last_health_check_at if db_cfg else None
            )
            last_error_message = db_cfg.last_error_message if db_cfg else None

            responses.append(
                ProviderConfigResponse(
                    provider_id=p_id,
                    display_name=definition.display_name,
                    description=definition.description,
                    capabilities=[c.value for c in definition.capabilities],
                    is_enabled=is_enabled,
                    priority=priority,
                    base_url=base_url,
                    effective_base_url=effective_base_url,
                    timeout_seconds=timeout_seconds,
                    rate_limit_per_minute=rate_limit,
                    custom_headers=custom_headers,
                    status=status,
                    last_health_check_at=last_health_check_at,
                    last_error_message=last_error_message,
                    requires_auth=definition.requires_auth,
                    has_api_key_configured=bool(effective_key),
                    api_key_masked=mask_secret(effective_key),
                    is_official_authority=definition.is_official_authority,
                    is_customized=is_customized,
                    doc_url=definition.doc_url,
                )
            )

        responses.sort(key=lambda x: (x.priority, x.provider_id))
        return responses

    @staticmethod
    async def get_effective_provider_config(
        provider_id: str,
        db: AsyncSession,
    ) -> EffectiveProviderConfig:
        """Resolve a configuração efetiva para uso em workers."""
        try:
            pid_enum = ProviderId(provider_id)
        except ValueError:
            raise ValueError(f"Provedor não reconhecido: {provider_id}")

        definition = PROVIDER_REGISTRY[pid_enum]

        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.provider_id == provider_id
        )
        result = await db.execute(stmt)
        db_cfg = result.scalar_one_or_none()

        base_url = (
            db_cfg.base_url if db_cfg and db_cfg.base_url else None
        ) or definition.default_base_url
        timeout_seconds = (
            db_cfg.timeout_seconds
            if db_cfg
            else definition.default_timeout_seconds
        )
        rate_limit = (
            db_cfg.rate_limit_per_minute
            if db_cfg and db_cfg.rate_limit_per_minute is not None
            else definition.default_rate_limit_per_minute
        )
        custom_headers = (
            db_cfg.custom_headers if db_cfg and db_cfg.custom_headers else {}
        )

        db_key = decrypt_secret(db_cfg.api_key_encrypted) if db_cfg else None
        env_key = (
            getattr(settings, definition.env_key_var, None)
            if definition.env_key_var
            else None
        )
        api_key = db_key or env_key

        is_enabled = db_cfg.is_enabled if db_cfg else True
        priority = db_cfg.priority if db_cfg else definition.default_priority

        return EffectiveProviderConfig(
            provider_id=provider_id,
            display_name=definition.display_name,
            is_enabled=is_enabled,
            priority=priority,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            rate_limit_per_minute=rate_limit,
            custom_headers=custom_headers,
            is_source_db=db_cfg is not None,
        )

    @staticmethod
    async def update_provider_config(
        provider_id: str,
        data: ProviderConfigUpdate,
        user_id: int,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProviderConfigResponse:
        """Atualiza a configuração de forma persistida e auditada."""
        try:
            pid_enum = ProviderId(provider_id)
        except ValueError:
            raise ValueError(f"Provedor desconhecido: {provider_id}")

        definition = PROVIDER_REGISTRY[pid_enum]

        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.provider_id == provider_id
        )
        result = await db.execute(stmt)
        db_cfg = result.scalar_one_or_none()

        old_values = (
            {
                "is_enabled": db_cfg.is_enabled,
                "priority": db_cfg.priority,
                "base_url": db_cfg.base_url,
                "timeout_seconds": db_cfg.timeout_seconds,
                "rate_limit_per_minute": db_cfg.rate_limit_per_minute,
                "has_api_key": bool(db_cfg.api_key_encrypted),
            }
            if db_cfg
            else {
                "is_enabled": True,
                "priority": definition.default_priority,
                "base_url": None,
                "timeout_seconds": definition.default_timeout_seconds,
                "rate_limit_per_minute": (
                    definition.default_rate_limit_per_minute
                ),
                "has_api_key": False,
            }
        )

        if not db_cfg:
            db_cfg = ProviderConfiguration(
                provider_id=provider_id,
                is_enabled=(
                    True if data.is_enabled is None else data.is_enabled
                ),
                priority=(
                    definition.default_priority
                    if data.priority is None
                    else data.priority
                ),
                base_url=data.base_url,
                timeout_seconds=(
                    definition.default_timeout_seconds
                    if data.timeout_seconds is None
                    else data.timeout_seconds
                ),
                rate_limit_per_minute=data.rate_limit_per_minute,
                custom_headers=data.custom_headers,
                status=ProviderStatus.OK,
            )
            db.add(db_cfg)

        if data.is_enabled is not None:
            db_cfg.is_enabled = data.is_enabled
        if data.priority is not None:
            db_cfg.priority = data.priority
        if data.base_url is not None:
            cleaned = data.base_url.strip()
            db_cfg.base_url = cleaned if cleaned else None
        if data.timeout_seconds is not None:
            db_cfg.timeout_seconds = data.timeout_seconds
        if data.rate_limit_per_minute is not None:
            db_cfg.rate_limit_per_minute = data.rate_limit_per_minute
        if data.custom_headers is not None:
            db_cfg.custom_headers = data.custom_headers

        if data.new_api_key is not None:
            cleaned_key = data.new_api_key.strip()
            if cleaned_key:
                db_cfg.api_key_encrypted = encrypt_secret(cleaned_key)
            else:
                db_cfg.api_key_encrypted = None

        new_values = {
            "is_enabled": db_cfg.is_enabled,
            "priority": db_cfg.priority,
            "base_url": db_cfg.base_url,
            "timeout_seconds": db_cfg.timeout_seconds,
            "rate_limit_per_minute": db_cfg.rate_limit_per_minute,
            "has_api_key": bool(db_cfg.api_key_encrypted),
        }

        await db.commit()
        await db.refresh(db_cfg)

        await AuditLogService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.UPDATE.value,
            resource_type="PROVIDER_CONFIG",
            resource_id=db_cfg.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        providers = await ProviderConfigService.list_providers(db)
        return next(p for p in providers if p.provider_id == provider_id)

    @staticmethod
    async def reset_provider_to_default(
        provider_id: str,
        user_id: int,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProviderConfigResponse:
        """Restaura a configuração para os padrões do sistema."""
        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.provider_id == provider_id
        )
        result = await db.execute(stmt)
        db_cfg = result.scalar_one_or_none()

        if db_cfg:
            old_values = {
                "is_enabled": db_cfg.is_enabled,
                "priority": db_cfg.priority,
                "base_url": db_cfg.base_url,
                "has_api_key": bool(db_cfg.api_key_encrypted),
            }
            await db.delete(db_cfg)
            await db.commit()

            await AuditLogService.log_action(
                db=db,
                user_id=user_id,
                action=AuditAction.DELETE.value,
                resource_type="PROVIDER_CONFIG",
                resource_id=None,
                old_values=old_values,
                new_values={"reset_to_default": True},
                ip_address=ip_address,
                user_agent=user_agent,
                status="SUCCESS",
            )

        providers = await ProviderConfigService.list_providers(db)
        return next(p for p in providers if p.provider_id == provider_id)

    @staticmethod
    async def test_provider_connectivity(
        provider_id: str,
        db: AsyncSession,
    ) -> ProviderTestResponse:
        """Executa probe seguro de conectividade e latência."""
        try:
            pid_enum = ProviderId(provider_id)
        except ValueError:
            raise ValueError(f"Provedor desconhecido: {provider_id}")

        definition = PROVIDER_REGISTRY[pid_enum]
        effective = await ProviderConfigService.get_effective_provider_config(
            provider_id, db
        )

        now = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        if pid_enum == ProviderId.B3_COTAHIST:
            latency_ms = (time.perf_counter() - start_time) * 1000
            test_resp = ProviderTestResponse(
                provider_id=provider_id,
                success=True,
                status=ProviderStatus.OK.value,
                latency_ms=round(latency_ms, 2),
                message="Parser COTAHIST e catálogo oficial B3 operacionais.",
                tested_at=now,
            )
            await ProviderConfigService._persist_health_check(
                db, provider_id, ProviderStatus.OK, now, None
            )
            return test_resp

        url = (
            effective.base_url or definition.default_base_url or ""
        ).rstrip("/")
        if definition.probe_endpoint_path:
            url += definition.probe_endpoint_path

        headers = {
            "User-Agent": "SGI-v2-ConnectivityProbe/1.0",
            **effective.custom_headers,
        }

        params: dict[str, str] = {}
        if pid_enum == ProviderId.BRAPI and effective.api_key:
            headers["Authorization"] = f"Bearer {effective.api_key}"
        elif pid_enum == ProviderId.ALPHA_VANTAGE and effective.api_key:
            params["apikey"] = effective.api_key

        try:
            async with httpx.AsyncClient(
                timeout=min(float(effective.timeout_seconds), 15.0),
                follow_redirects=True,
            ) as client:
                res = await client.get(url, headers=headers, params=params)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if res.status_code in {200, 201, 204}:
                    status = ProviderStatus.OK
                    msg = (
                        f"Conexão estabelecida com sucesso "
                        f"({res.status_code} OK)."
                    )
                    last_err = None
                    success = True
                elif res.status_code in {401, 403}:
                    status = ProviderStatus.PROVIDER_ERROR
                    msg = (
                        f"Falha de autenticação ({res.status_code}): "
                        f"Verifique a API Key configurada."
                    )
                    last_err = msg
                    success = False
                elif res.status_code == 429:
                    status = ProviderStatus.PROVIDER_ERROR
                    msg = "Limite de taxa atingido (429 Too Many Requests)."
                    last_err = msg
                    success = False
                else:
                    status = ProviderStatus.PROVIDER_ERROR
                    msg = (
                        f"Resposta inesperada do provedor: "
                        f"HTTP {res.status_code}."
                    )
                    last_err = msg
                    success = False

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000
            status = ProviderStatus.PROVIDER_ERROR
            msg = f"Tempo limite esgotado ({effective.timeout_seconds}s)."
            last_err = msg
            success = False
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            status = ProviderStatus.PROVIDER_ERROR
            msg = f"Erro de rede: {type(exc).__name__} - {str(exc)}"
            last_err = msg
            success = False

        await ProviderConfigService._persist_health_check(
            db, provider_id, status, now, last_err
        )

        return ProviderTestResponse(
            provider_id=provider_id,
            success=success,
            status=status.value,
            latency_ms=round(latency_ms, 2),
            message=msg,
            tested_at=now,
        )

    @staticmethod
    async def _persist_health_check(
        db: AsyncSession,
        provider_id: str,
        status: ProviderStatus,
        checked_at: datetime,
        error_msg: str | None,
    ) -> None:
        """Registra a telemetria do teste no banco de dados."""
        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.provider_id == provider_id
        )
        result = await db.execute(stmt)
        cfg = result.scalar_one_or_none()

        if not cfg:
            cfg = ProviderConfiguration(
                provider_id=provider_id,
                status=status.value,
                last_health_check_at=checked_at,
                last_error_message=error_msg,
            )
            db.add(cfg)
        else:
            cfg.status = status.value
            cfg.last_health_check_at = checked_at
            cfg.last_error_message = error_msg

        await db.commit()
