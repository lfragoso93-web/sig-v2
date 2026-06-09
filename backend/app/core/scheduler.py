import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


def start_scheduler(db_factory) -> None:
    """
    Registra jobs e inicia o scheduler.
    db_factory: callable que retorna uma Session do SQLAlchemy.
    """

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour="9-18", minute="*/15"),
        id="update_quotes",
        name="Atualizar cotacoes BRAPI",
    )
    async def update_quotes_job():
        from app.services.quote_service import update_all_quotes
        db = db_factory()
        try:
            await update_all_quotes(db)
        except Exception as e:
            logger.error(f"[scheduler] Erro ao atualizar cotacoes: {e}")
        finally:
            db.close()

    scheduler.start()
    logger.info("Scheduler iniciado — cotacoes atualizadas a cada 15min (seg-sex 9h-18h)")
