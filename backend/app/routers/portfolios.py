import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.asset_portfolio_insight import AssetPortfolioInsightResponse
from app.schemas.portfolio import (
    ClassTargetWithCurrent,
    CSVImportResponse,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
)
from app.schemas.portfolio_ai_analysis import (
    AiQuestionRequest,
    AiQuestionResponse,
    ContributionSimulationRequest,
    ContributionSimulationResponse,
    PortfolioAiAnalysisResponse,
)
from app.schemas.portfolio_analysis import PortfolioConsolidatedAnalysisResponse
from app.schemas.portfolio_intraday_reconciliation import IntradayReconciliationResponse
from app.schemas.portfolio_positions import PositionGroupResponse
from app.schemas.portfolio_summary import PortfolioSummaryResponse
from app.services import csv_import_service
from app.services.canonical_positions_service import (
    export_canonical_positions_csv,
    get_canonical_portfolio_positions,
)
from app.services.class_target_service import get_targets_with_current
from app.services.csv_snapshot_rebuild_service import rebuild_snapshots_after_csv_import
from app.services.csv_ticker_resolution import enrich_csv_dry_run_with_ticker_resolution
from app.services.portfolio_delete_service import delete_portfolio_safely
from app.services.portfolio_intraday_reconciliation_service import (
    get_intraday_reconciliation,
)
from app.services.portfolio_service import (
    create_portfolio,
    get_asset_distribution,
    get_portfolio,
    invalidate_portfolio_cache,
    list_portfolios,
    update_portfolio,
)
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.rentabilidade_cache_service import invalidate_rentabilidade_cache

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolios"])

_CSV_MESSAGE_EXACT = {
    "CSV file is empty or invalid": "O arquivo CSV está vazio ou inválido",
    "Empty row, skipping": "Linha vazia; o lançamento foi ignorado",
    "ticker is required": "O campo ticker é obrigatório",
    "asset_type is required": "O campo asset_type é obrigatório",
    "operation is required": "O campo operation é obrigatório",
    "quantity is required": "O campo quantity é obrigatório",
    "price is required": "O campo price é obrigatório",
    "quantity must be positive": "A quantidade deve ser maior que zero",
    "price must be positive": "O preço deve ser maior que zero",
    "fees cannot be negative": "As taxas não podem ser negativas",
    "Unauthorized: Portfolio belongs to different user": "A carteira pertence a outro usuário",
}


def _localize_csv_message(message: str) -> str:
    if message in _CSV_MESSAGE_EXACT:
        return _CSV_MESSAGE_EXACT[message]

    replacements = (
        ("Missing required headers:", "Colunas obrigatórias ausentes:"),
        ("asset_type '", "Tipo de ativo '"),
        ("' not supported. Valid:", "' não suportado. Valores aceitos:"),
        ("operation '", "Operação '"),
        ("' not valid. Valid:", "' inválida. Valores aceitos:"),
        ("quantity '", "Quantidade '"),
        ("' is not a valid number", "' não é um número válido"),
        ("price '", "Preço '"),
        ("date '", "Data '"),
        ("' format not recognized (use YYYY-MM-DD)", "' em formato inválido; use AAAA-MM-DD"),
        ("' is in the future", "' está no futuro"),
        ("fees '", "Taxas '"),
        ("currency '", "Moeda '"),
        ("' may not be valid, defaulting to BRL", "' pode ser inválida; será usado BRL"),
        ("Portfolio ", "Carteira "),
        (" not found", " não encontrada"),
        ("Database error:", "Erro ao gravar no banco de dados:"),
        ("Error parsing CSV:", "Erro ao interpretar o CSV:"),
    )
    localized = message
    for source, target in replacements:
        localized = localized.replace(source, target)
    return localized


def _localize_csv_result(result: dict) -> dict:
    result["global_errors"] = [
        _localize_csv_message(str(message))
        for message in result.get("global_errors", [])
    ]
    for row in result.get("rows", []):
        row["errors"] = [
            _localize_csv_message(str(message))
            for message in row.get("errors", [])
        ]
        row["warnings"] = [
            _localize_csv_message(str(message))
            for message in row.get("warnings", [])
        ]
    return result


async def _refresh_after_csv_import(portfolio_id: int) -> None:
    await invalidate_portfolio_cache(portfolio_id)
    await invalidate_rentabilidade_cache(portfolio_id)


@router.get("/", response_model=list[PortfolioResponse])
async def list_user_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_user_portfolio(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_portfolio(db, current_user.id, data)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio(db, portfolio_id, current_user.id)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_user_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await delete_portfolio_safely(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummaryResponse)
async def portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_canonical_portfolio_summary(db, portfolio_id, current_user.id)


@router.get(
    "/{portfolio_id}/positions",
    response_model=list[PositionGroupResponse],
    response_model_exclude_unset=True,
)
async def portfolio_positions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_canonical_portfolio_positions(db, portfolio_id, current_user.id)


@router.get(
    "/{portfolio_id}/assets/{ticker}/insights",
    response_model=AssetPortfolioInsightResponse,
)
async def get_asset_portfolio_insights(
    portfolio_id: int,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna correlacao da posicao com a carteira e insights de IA (Issue #58)."""
    from app.services.asset_portfolio_insight_service import (
        asset_portfolio_insight_service,
    )
    return await asset_portfolio_insight_service.get_insight(
        db, portfolio_id, current_user.id, ticker
    )


@router.get(
    "/{portfolio_id}/analysis",
    response_model=PortfolioConsolidatedAnalysisResponse,
    summary="Análise determinística e diagnósticos de alocação por classe (Issue #360)",
)
async def get_portfolio_analysis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna análise determinística por classe de ativos e diagnósticos de rebalanceamento."""
    from app.services.portfolio_analysis_service import PortfolioAnalysisService

    service = PortfolioAnalysisService(db)
    try:
        return await service.get_portfolio_analysis(portfolio_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{portfolio_id}/ai-analysis",
    response_model=PortfolioAiAnalysisResponse,
    summary="Camada de IA para análise explicável de carteiras e ativos (Issue #361)",
)
async def get_portfolio_ai_analysis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna síntese explicativa em linguagem natural gerada por IA com base nas métricas determinísticas."""
    from app.services.portfolio_ai_analysis_service import PortfolioAiAnalysisService

    service = PortfolioAiAnalysisService(db)
    try:
        return await service.get_ai_analysis(portfolio_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{portfolio_id}/ai-analysis/simulate-contribution",
    response_model=ContributionSimulationResponse,
    summary="Simulação inteligente de aporte e impacto no rebalanceamento (Issue #361)",
)
async def simulate_portfolio_contribution(
    portfolio_id: int,
    payload: ContributionSimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simula a distribuição ótima de um novo aporte para acelerar o rebalanceamento da carteira."""
    from app.services.portfolio_ai_analysis_service import PortfolioAiAnalysisService

    service = PortfolioAiAnalysisService(db)
    try:
        return await service.simulate_contribution(portfolio_id, current_user.id, payload.contribution_amount, strategy=payload.strategy)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{portfolio_id}/ai-analysis/ask",
    response_model=AiQuestionResponse,
    summary="Q&A explicável ancorado estritamente nas métricas determinísticas (Issue #361)",
)
async def ask_portfolio_ai(
    portfolio_id: int,
    payload: AiQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Responde perguntas sobre diversificação, riscos e rebalanceamento ancoradas nos dados consolidados."""
    from app.services.portfolio_ai_analysis_service import PortfolioAiAnalysisService

    service = PortfolioAiAnalysisService(db)
    try:
        return await service.answer_ai_question(portfolio_id, current_user.id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{portfolio_id}/asset-distribution")
async def asset_distribution(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_asset_distribution(db, portfolio_id, current_user.id)


@router.get(
    "/{portfolio_id}/reconciliation/intraday",
    response_model=IntradayReconciliationResponse,
)
async def intraday_reconciliation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_intraday_reconciliation(db, portfolio_id, current_user.id)


@router.get(
    "/{portfolio_id}/targets-with-current",
    response_model=list[ClassTargetWithCurrent],
)
async def get_portfolio_targets_with_current(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_distribution = await get_asset_distribution(db, portfolio_id, current_user.id)
    return await get_targets_with_current(db, portfolio_id, current_distribution)


@router.post("/{portfolio_id}/import-csv", response_model=CSVImportResponse)
async def import_portfolio_csv(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dry_run: bool = True,
    source: str = Query("auto", description="Origem do arquivo CSV: auto, canonical ou b3"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    result = await csv_import_service.import_transactions_csv(
        db=db,
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        file=file,
        dry_run=dry_run,
        source=source,
    )
    if dry_run:
        result = await enrich_csv_dry_run_with_ticker_resolution(result)
    result = _localize_csv_result(result)
    if (
        not dry_run
        and result.get("success") is True
        and result.get("imported_count", 0) > 0
    ):
        await _refresh_after_csv_import(portfolio_id)
        background_tasks.add_task(rebuild_snapshots_after_csv_import, portfolio_id)
    return result


@router.get("/{portfolio_id}/export-csv", tags=["csv-import"])
async def export_portfolio_csv(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    csv_content = await csv_import_service.export_transactions_csv(db, portfolio_id)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="portfolio_{portfolio_id}_transactions.csv"'
            )
        },
    )


@router.get("/{portfolio_id}/positions/export-csv", tags=["positions", "export"])
@router.get("/{portfolio_id}/export-positions-csv", tags=["positions", "export"])
async def export_portfolio_positions_csv(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    groups = await get_canonical_portfolio_positions(db, portfolio_id, current_user.id)
    csv_content = export_canonical_positions_csv(groups)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="portfolio_{portfolio_id}_positions.csv"'
            )
        },
    )
