"""Model de controle do job de bootstrap/sync de dividendos FIIs."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, func
)
from app.models.base import Base


class DividendsSyncJob(Base):
    """
    Tabela de estado, lock e auditoria do job de bootstrap/sync de
    dividendos FIIs via BRAPI.

    Uso:
        - Um registro por job_name (ex: 'fii_dividends_bootstrap').
        - locked_by / locked_at controlam execucao concorrente.
        - last_cursor_date e o cursor para sync incremental: proxima
          execucao busca a partir de (last_cursor_date - LOOKBACK_DAYS).
        - error_message registra o traceback / mensagem da ultima falha.
    """
    __tablename__ = 'dividends_sync_jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificador do job (ex: 'fii_dividends_bootstrap', 'fii_dividends_incremental')
    job_name = Column(String(100), nullable=False, unique=True, index=True)

    # Status atual: 'idle', 'running', 'success', 'error'
    status = Column(String(20), nullable=False, default='idle')

    # Timestamps de execucao
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)

    # Cursor para sync incremental
    # Armazena a data do evento mais recente sincronizado com sucesso.
    # O proximo sync busca a partir de (last_cursor_date - LOOKBACK_DAYS)
    # para absorver correcoes retroativas da BRAPI.
    last_cursor_date = Column(Date, nullable=True)

    # Metricas do ultimo run
    last_run_assets_processed = Column(Integer, nullable=True)
    last_run_events_created = Column(Integer, nullable=True)
    last_run_events_updated = Column(Integer, nullable=True)
    last_run_errors = Column(Integer, nullable=True)

    # Lock distribuido simples
    # locked_by: identificador da instancia que adquiriu o lock (ex: hostname)
    # locked_at: timestamp de quando o lock foi adquirido
    locked_by = Column(String(255), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)

    # Ultimo erro registrado
    error_message = Column(Text, nullable=True)

    # Auditoria
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def is_locked(self, lock_timeout_minutes: int = 60) -> bool:
        """
        Verifica se o job esta com lock ativo e nao expirado.

        Um lock e considerado expirado se locked_at for anterior a
        (agora - lock_timeout_minutes), prevenindo lock eterno em caso
        de crash da instancia que adquiriu o lock.
        """
        if not self.locked_by or not self.locked_at:
            return False
        from datetime import timezone, timedelta
        expiry = self.locked_at + timedelta(minutes=lock_timeout_minutes)
        return datetime.now(timezone.utc) < expiry

    def __repr__(self) -> str:
        return (
            f"<DividendsSyncJob job_name={self.job_name!r} "
            f"status={self.status!r} "
            f"last_cursor_date={self.last_cursor_date!r}>"
        )
