from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """
    Configurações do sistema editáveis pelo SuperAdmin via painel.
    Chave-valor para flexibilidade máxima.
    """
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # visível sem auth

    def __repr__(self) -> str:
        return f"<SystemConfig key={self.key}>"


# Configurações padrão do sistema (seed)
DEFAULT_CONFIGS = [
    {"key": "app_name", "value": "SGI", "description": "Nome do sistema", "is_public": True},
    {"key": "app_tagline", "value": "Sistema de Gestão de Investimentos", "description": "Subtítulo do sistema", "is_public": True},
    {"key": "allow_registration", "value": "true", "description": "Permite auto-registro de novos usuários", "is_public": True},
    {"key": "max_portfolios_per_user", "value": "10", "description": "Limite de carteiras por usuário", "is_public": False},
    {"key": "brapi_rate_limit", "value": "300", "description": "Requisições por hora na BRAPI", "is_public": False},
    {"key": "ai_analysis_enabled", "value": "true", "description": "Habilita análise com IA (Gemini)", "is_public": False},
    {"key": "maintenance_mode", "value": "false", "description": "Modo manutenção — bloqueia acesso de usuários", "is_public": True},
    {
        "key": "market_calendar.b3_source_url",
        "value": (
            "https://www.b3.com.br/pt_br/noticias/"
            "calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm"
        ),
        "description": "Fonte oficial B3 do calendario de mercado para auditoria.",
        "is_public": False,
    },
    {
        "key": "market_calendar.b3_source_year",
        "value": "2026",
        "description": "Ano da fonte B3 usada pela auditoria de calendario.",
        "is_public": False,
    },
]
