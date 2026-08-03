"""
Asset Onboarding Service.

Executado como BackgroundTask ao criar um novo ativo ou transação. O onboarding
agora delega para o pipeline único de mercado por ativo, que centraliza:

  - histórico de preços;
  - logo/metadados faltantes;
  - eventos/proventos globais;
"""
import logging

from app.models.asset import AssetType
from app.core.asset_types import NO_QUOTE_TYPES
from app.core.database import AsyncSessionLocal
from app.services.asset_market_pipeline_service import sync_asset_market_data

logger = logging.getLogger(__name__)


async def run_onboarding(ticker: str, asset_type: str) -> None:
    ticker_norm = ticker.upper().strip()
    logger.info("[onboarding] iniciando pipeline único para %s (%s)", ticker_norm, asset_type)

    try:
        at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
    except ValueError:
        logger.warning("[onboarding] asset_type invalido: %s — abortando", asset_type)
        return

    if at in NO_QUOTE_TYPES:
        logger.info(
            "[onboarding] %s (%s): tipo sem dados de mercado — pulando pipeline",
            ticker_norm,
            at.value,
        )
        return

    async with AsyncSessionLocal() as db:
        try:
            result = await sync_asset_market_data(
                db=db,
                ticker=ticker_norm,
                asset_type=at,
                full=True,
                sync_prices=True,
                sync_logo=True,
                sync_events=True,
                commit=True,
            )
            logger.info(
                "[onboarding] %s concluído: prices=%s logo=%s events=%s",
                ticker_norm,
                result.prices_inserted,
                result.logo_updated,
                result.events_synced,
            )
        except Exception as e:
            logger.error("[onboarding] %s: falha no pipeline único: %s", ticker_norm, e)
