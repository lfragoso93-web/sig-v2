"""
Testes de integracao para DividendsSyncService (Sprint 5B).

Fluxo testado:
  - Lock: adquire, impede concorrencia, expira corretamente
  - Bootstrap: busca historico a partir de N anos sem cursor
  - Incremental: usa cursor para janela reduzida
  - Upsert: cria novos eventos, atualiza valor se mudou, ignora duplicatas
  - Sem FIIs: encerra graciosamente sem erros
"""
import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType, AssetCurrency
from app.models.asset_dividend import AssetDividend
from app.models.dividends_sync_job import DividendsSyncJob
from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioPosition
from app.models.user import User
from app.services.dividends_sync_service import (
    BOOTSTRAP_YEARS_BACK,
    JOB_NAME_BOOTSTRAP,
    JOB_NAME_INCREMENTAL,
    LOOKBACK_DAYS,
    run_fii_dividends_sync,
    _get_or_create_job,
    _acquire_lock,
    _upsert_asset_dividends,
    _fetch_fii_tickers,
)
from app.integrations.brapi_fii_dividends_client import FiiDividendEvent


# ─── Fixtures de apoio ────────────────────────────────────────────────────────

async def _make_fii_asset(db: AsyncSession, ticker: str) -> Asset:
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.FII,
        currency=AssetCurrency.BRL,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def _make_position(db: AsyncSession, portfolio_id: int, asset: Asset, qty: float = 100.0) -> PortfolioPosition:
    pos = PortfolioPosition(
        portfolio_id=portfolio_id,
        asset_id=asset.id,
        quantity=qty,
        average_price=Decimal("10.00"),
    )
    db.add(pos)
    await db.flush()
    return pos


def _make_event(ticker: str, ex_date: date, value: float = 1.0, raw_type: str = "RENDIMENTO") -> FiiDividendEvent:
    return FiiDividendEvent(
        ticker=ticker,
        ex_date=ex_date,
        payment_date=ex_date,
        declared_date=ex_date,
        value_per_unit=Decimal(str(value)),
        dividend_type="RENDIMENTO",
        raw_type=raw_type,
    )


# ─── Testes de Lock ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestLockBehavior:

    async def test_acquire_lock_cria_job_se_inexistente(self, db: AsyncSession):
        """_get_or_create_job cria novo registro quando nao existe."""
        job = await _get_or_create_job(db, "test_job")
        assert job.id is not None
        assert job.job_name == "test_job"
        assert job.status == "idle"

    async def test_acquire_lock_retorna_true_em_job_livre(self, db: AsyncSession):
        job = await _get_or_create_job(db, JOB_NAME_INCREMENTAL)
        result = await _acquire_lock(db, job)
        assert result is True
        assert job.status == "running"
        assert job.locked_by is not None
        assert job.locked_at is not None

    async def test_acquire_lock_retorna_false_em_job_bloqueado(self, db: AsyncSession):
        job = await _get_or_create_job(db, JOB_NAME_INCREMENTAL)
        # Simula lock ativo recente
        job.locked_by = "outro-host"
        job.locked_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        job.status = "running"
        await db.flush()

        result = await _acquire_lock(db, job)
        assert result is False

    async def test_acquire_lock_permite_apos_expiracao(self, db: AsyncSession):
        job = await _get_or_create_job(db, JOB_NAME_INCREMENTAL)
        # Simula lock expirado ha mais de 60min
        job.locked_by = "host-morto"
        job.locked_at = datetime.now(timezone.utc) - timedelta(minutes=90)
        job.status = "running"
        await db.flush()

        result = await _acquire_lock(db, job)
        assert result is True


# ─── Testes de _fetch_fii_tickers ────────────────────────────────────────────

@pytest.mark.asyncio
class TestFetchFiiTickers:

    async def test_sem_fii_retorna_lista_vazia(self, db: AsyncSession, portfolio: Portfolio):
        tickers = await _fetch_fii_tickers(db)
        assert tickers == []

    async def test_fii_com_posicao_ativa_retornado(self, db: AsyncSession, portfolio: Portfolio):
        asset = await _make_fii_asset(db, "MXRF11")
        await _make_position(db, portfolio.id, asset, qty=100.0)

        tickers = await _fetch_fii_tickers(db)
        assert len(tickers) == 1
        assert tickers[0][1] == "MXRF11"

    async def test_fii_com_posicao_zero_nao_retornado(self, db: AsyncSession, portfolio: Portfolio):
        asset = await _make_fii_asset(db, "HGLG11")
        await _make_position(db, portfolio.id, asset, qty=0.0)

        tickers = await _fetch_fii_tickers(db)
        assert tickers == []

    async def test_fii_aparece_uma_vez_mesmo_em_multiplas_carteiras(self, db: AsyncSession, user: User):
        from app.models.portfolio import Portfolio
        p1 = Portfolio(user_id=user.id, name="P1", description="")
        p2 = Portfolio(user_id=user.id, name="P2", description="")
        db.add_all([p1, p2])
        await db.flush()

        asset = await _make_fii_asset(db, "VISC11")
        await _make_position(db, p1.id, asset, qty=50.0)
        await _make_position(db, p2.id, asset, qty=50.0)

        tickers = await _fetch_fii_tickers(db)
        ticker_list = [t for _, t in tickers]
        assert ticker_list.count("VISC11") == 1


# ─── Testes de _upsert_asset_dividends ───────────────────────────────────────

@pytest.mark.asyncio
class TestUpsertAssetDividends:

    async def test_cria_novo_evento(self, db: AsyncSession, portfolio: Portfolio):
        asset = await _make_fii_asset(db, "KNRI11")
        events = [_make_event("KNRI11", date(2024, 6, 1), value=0.85)]

        created, updated = await _upsert_asset_dividends(db, events, asset.id)
        assert created == 1
        assert updated == 0

    async def test_nao_duplica_evento_existente(self, db: AsyncSession, portfolio: Portfolio):
        asset = await _make_fii_asset(db, "XPML11")
        ev_date = date(2024, 5, 1)

        # Insere o evento pela primeira vez
        events = [_make_event("XPML11", ev_date, value=0.90)]
        await _upsert_asset_dividends(db, events, asset.id)

        # Tenta inserir novamente com mesmo valor
        created, updated = await _upsert_asset_dividends(db, events, asset.id)
        assert created == 0
        assert updated == 0

    async def test_atualiza_valor_se_mudou(self, db: AsyncSession):
        asset = await _make_fii_asset(db, "HFOF11")
        ev_date = date(2024, 4, 1)

        events_v1 = [_make_event("HFOF11", ev_date, value=0.70)]
        await _upsert_asset_dividends(db, events_v1, asset.id)

        events_v2 = [_make_event("HFOF11", ev_date, value=0.75)]
        created, updated = await _upsert_asset_dividends(db, events_v2, asset.id)

        assert created == 0
        assert updated == 1

    async def test_ignora_evento_com_valor_zero_ou_negativo(self, db: AsyncSession):
        asset = await _make_fii_asset(db, "BCFF11")

        events = [
            _make_event("BCFF11", date(2024, 3, 1), value=0.0),
            _make_event("BCFF11", date(2024, 3, 2), value=-1.0),
        ]
        created, updated = await _upsert_asset_dividends(db, events, asset.id)
        assert created == 0
        assert updated == 0

    async def test_ignora_evento_sem_ex_date(self, db: AsyncSession):
        asset = await _make_fii_asset(db, "CPTS11")
        ev = FiiDividendEvent(
            ticker="CPTS11",
            ex_date=None,
            payment_date=None,
            declared_date=None,
            value_per_unit=Decimal("1.00"),
            dividend_type="RENDIMENTO",
            raw_type="RENDIMENTO",
        )
        created, updated = await _upsert_asset_dividends(db, [ev], asset.id)
        assert created == 0


# ─── Testes de run_fii_dividends_sync ────────────────────────────────────────

@pytest.mark.asyncio
class TestRunFiiDividendsSync:

    async def test_sem_fii_ativo_encerra_com_sucesso(self, db: AsyncSession):
        """Sem FIIs na carteira, job encerra com sucesso e zero eventos."""
        with patch(
            "app.services.dividends_sync_service.get_fii_dividends_chunked",
            new_callable=AsyncMock,
        ) as mock_fetch:
            result = await run_fii_dividends_sync(db)

        assert result.success is True
        assert result.assets_processed == 0
        assert result.events_created == 0
        mock_fetch.assert_not_called()

    async def test_bootstrap_busca_desde_n_anos_atras(self, db: AsyncSession, portfolio: Portfolio):
        """Em modo bootstrap (sem cursor), start_date deve ser ~5 anos atras."""
        asset = await _make_fii_asset(db, "MXRF11")
        await _make_position(db, portfolio.id, asset)

        captured_start: list[date] = []

        async def fake_fetch(tickers, start_date, end_date):
            captured_start.append(start_date)
            return {"MXRF11": [_make_event("MXRF11", date(2024, 1, 1), value=0.80)]}

        with patch(
            "app.services.dividends_sync_service.get_fii_dividends_chunked",
            side_effect=fake_fetch,
        ):
            result = await run_fii_dividends_sync(db, force_bootstrap=True)

        assert result.success is True
        assert result.events_created == 1

        expected_start = date.today() - timedelta(days=BOOTSTRAP_YEARS_BACK * 365)
        diff = abs((captured_start[0] - expected_start).days)
        assert diff <= 1  # tolerancia de 1 dia

    async def test_incremental_usa_cursor_como_base(self, db: AsyncSession, portfolio: Portfolio):
        """Em modo incremental, start_date deve ser cursor - LOOKBACK_DAYS."""
        asset = await _make_fii_asset(db, "HGLG11")
        await _make_position(db, portfolio.id, asset)

        # Cria job com cursor pre-definido
        cursor = date(2024, 6, 1)
        job = DividendsSyncJob(job_name=JOB_NAME_INCREMENTAL, status="success", last_cursor_date=cursor)
        db.add(job)
        await db.flush()

        captured_start: list[date] = []

        async def fake_fetch(tickers, start_date, end_date):
            captured_start.append(start_date)
            return {}

        with patch(
            "app.services.dividends_sync_service.get_fii_dividends_chunked",
            side_effect=fake_fetch,
        ):
            result = await run_fii_dividends_sync(db, force_bootstrap=False)

        expected_start = cursor - timedelta(days=LOOKBACK_DAYS)
        assert captured_start[0] == expected_start
        assert result.success is True

    async def test_lock_impede_execucao_concorrente(self, db: AsyncSession, portfolio: Portfolio):
        """Job ja em execucao impede novo run (retorna sem erro, sem processar)."""
        asset = await _make_fii_asset(db, "XPML11")
        await _make_position(db, portfolio.id, asset)

        # Simula job com lock ativo
        job = DividendsSyncJob(
            job_name=JOB_NAME_INCREMENTAL,
            status="running",
            locked_by="outro-host",
            locked_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(job)
        await db.flush()

        with patch(
            "app.services.dividends_sync_service.get_fii_dividends_chunked",
            new_callable=AsyncMock,
        ) as mock_fetch:
            result = await run_fii_dividends_sync(db, force_bootstrap=False)

        mock_fetch.assert_not_called()
        assert result.success is False
        assert result.events_created == 0

    async def test_erro_em_ticker_nao_interrompe_demais(self, db: AsyncSession, portfolio: Portfolio):
        """Erro ao fazer upsert de um ticker nao deve impedir os outros."""
        asset1 = await _make_fii_asset(db, "MXRF11")
        asset2 = await _make_fii_asset(db, "HGLG11")
        await _make_position(db, portfolio.id, asset1)
        await _make_position(db, portfolio.id, asset2)

        call_count = 0

        async def fake_fetch(tickers, start_date, end_date):
            return {
                "MXRF11": [_make_event("MXRF11", date(2024, 3, 1), value=0.80)],
                "HGLG11": [_make_event("HGLG11", date(2024, 3, 1), value=1.20)],
            }

        original_upsert = __import__(
            "app.services.dividends_sync_service", fromlist=["_upsert_asset_dividends"]
        )._upsert_asset_dividends

        async def patched_upsert(db, events, asset_id):
            nonlocal call_count
            call_count += 1
            # Simula falha no primeiro ticker
            if call_count == 1:
                raise RuntimeError("Erro simulado no primeiro ticker")
            return await original_upsert(db, events, asset_id)

        with patch("app.services.dividends_sync_service.get_fii_dividends_chunked", side_effect=fake_fetch):
            with patch("app.services.dividends_sync_service._upsert_asset_dividends", side_effect=patched_upsert):
                result = await run_fii_dividends_sync(db, force_bootstrap=True)

        assert result.errors >= 1
        # Segundo ticker deve ter sido processado (events_created >= 1)
        assert result.events_created >= 1
