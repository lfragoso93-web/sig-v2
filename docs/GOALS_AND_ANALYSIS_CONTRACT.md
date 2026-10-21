# Contrato Canônico de Metas e Análise de Carteira

> Issue: #246  
> Data: 21/10/2026  
> Branch: `stable-15jun`  
> Referências: Issues #241, #360, #361, #57, #79

---

## 1. Contexto e Objetivo

O Macroprojeto Metas + Análise de Carteira (#246) unifica os objetivos financeiros globais da carteira (patrimônio, proventos, rentabilidade e metas livres) com a estratégia de distribuição percentual por classe de ativos e o motor analítico de rebalanceamento.

Com a conclusão dos motores analíticos determinísticos (#360), da camada explicativa de IA (#361) e da reconciliação canônica do modelo ORM de Metas com o schema físico do PostgreSQL, este contrato estabelece as garantias de persistência, tolerância zero a drift no Alembic e navegação unificada na interface.

---

## 2. Modelo de Dados e Eliminação de Deriva (Alembic Drift)

### 2.1 Schema Físico e ORM Canônico (`goals`)

A tabela física `goals` no PostgreSQL possui a seguinte especificação canônica:

| Coluna | Tipo PostgreSQL | Tipo SQLAlchemy | Nulo | Default | Descrição |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `Integer` | Não | `nextval(...)` | Chave primária autoincrementada (índice `ix_goals_id`) |
| `portfolio_id` | `INTEGER` | `Integer, ForeignKey("portfolios.id", ondelete="CASCADE")` | Não | - | Chave estrangeira com cascade e índice `ix_goals_portfolio_id` |
| `name` | `VARCHAR(150)` | `String(150)` | Não | - | Nome da meta |
| `goal_type` | `VARCHAR` | `String` | Não | `'LIVRE'` | Tipo: `PATRIMONIO`, `PROVENTOS`, `RENTABILIDADE`, `LIVRE` |
| `target_value` | `NUMERIC(18,2)` | `Numeric(18, 2)` | Não | - | Valor alvo estabelecido |
| `target_date` | `DATE` | `Date` | Sim | `NULL` | Data limite projetada ou desejada |
| `description` | `TEXT` | `Text` | Sim | `NULL` | Notas ou estratégia da meta |
| `is_active` | `BOOLEAN` | `Boolean` | Não | `true` | Indicador se a meta está ativa |
| `created_at` | `TIMESTAMPTZ` | `DateTime(timezone=True)` | Sim | `now()` | Timestamp de criação |
| `updated_at` | `TIMESTAMPTZ` | `DateTime(timezone=True)` | Sim | `now()` | Timestamp da última atualização |
| `current_value` | `DOUBLE PRECISION`| `Float` | Não | `0.0` | Valor atual (tempo real ou informado) |
| `base_value` | `DOUBLE PRECISION`| `Float` | Não | `0.0` | Valor base inicial da meta |
| `monthly_contribution` | `DOUBLE PRECISION`| `Float` | Sim | `NULL` | Aporte mensal projetado |

### 2.2 Gate de Deriva Alembic (`alembic_drift_gate.py`)

Com a reconciliação do modelo `Goal` em `backend/app/models/goal.py`, a exceção temporária concedida no gate de governança foi definitivamente encerrada:

```python
ALLOWED_DRIFT_TABLES: frozenset[str] = frozenset()
```

Qualquer alteração em modelos ou migrations que gere operações de autogenerate no Alembic resultará em falha imediata (*fail-closed*), assegurando 100% de paridade entre o SQLAlchemy MetaData e o banco de dados.

---

## 3. Arquitetura Funcional e Reconciliação Semântica

### 3.1 Metas Globais vs. Alocação por Classe

O sistema opera dois níveis complementares de metas para cada carteira:

1. **Metas Financeiras Globais (`goals`)**:
   - `PATRIMONIO`: Calculada em tempo real a partir de `get_portfolio_summary`.
   - `PROVENTOS`: Calculada a partir da média mensal líquida canônica de proventos em BRL dos últimos 12 meses (`load_portfolio_dividend_entitlements`).
   - `RENTABILIDADE`: Calculada a partir do snapshot mais recente de rentabilidade acumulada (`PortfolioSnapshot`).
   - `LIVRE`: Informada e mantida manualmente pelo usuário.

2. **Alocação Alvo por Classe de Ativo (`portfolio_class_targets`)**:
   - Percentuais alvo definidos por classe (ex.: Ações 40%, FIIs 30%, Renda Fixa 30%).
   - Comparados contra a posição real atual (`targets-with-current`).
   - Consumidos diretamente pelo motor de Análise de Carteira (`PortfolioAnalysisEngine`).

### 3.2 Conexão na Interface do Usuário

A página `/carteira/metas` integra os dois domínios:
- Exibe os KPIs de metas ativas, concluídas e progresso médio.
- Seção **Alocação Alvo por Classe de Ativo**: exibe o percentual atual vs. alvo por classe de ativo com barras visuais e badges de desvio.
- Link direto de navegação com ação clara: **"Análise & Rebalanceamento"** direcionando para `/carteira/analise`.
- Link de ajuste: **"Configurar"** direcionando para a tela de configurações de distribuição de ativos.

---

## 4. Invariantes de Governança e Testes

1. **DB-First e Determinístico**: Todas as projeções e enriquecimentos de metas são calculados a partir de dados canônicos locais, sem requisições externas em runtime.
2. **Zero Drift**: `alembic_drift_gate` deve rodar em CI contra `ALLOWED_DRIFT_TABLES = frozenset()`.
3. **Cascade Integrity**: Deleção de carteira remove automaticamente as metas vinculadas via foreign key ON DELETE CASCADE.
