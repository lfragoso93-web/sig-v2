from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Registra e inicia os jobs periódicos."""
    from app.services.quote_service import refresh_active_quotes
    from app.services.treasury_service import refresh_treasury_rates

    # Atualiza cotações de ativos ativos a cada 5 minutos (horário de mercado)
    scheduler.add_job(
        refresh_active_quotes,
        trigger=IntervalTrigger(minutes=5),
        id="refresh_quotes",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Atualiza taxas do Tesouro Direto a cada hora
    scheduler.add_job(
        refresh_treasury_rates,
        trigger=IntervalTrigger(hours=1),
        id="refresh_treasury",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info("⏰ Scheduler iniciado")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("⏰ Scheduler encerrado")
