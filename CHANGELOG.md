# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Referencias Tecnicas] - Anotacoes para sprints futuras

### Fonte: https://www.traders.com.br/blog/posts/api-financeira-python-mercado-como-usar

---

#### Sprint 5 (Cotacoes e Integracoes de Mercado) — referencias

**yfinance com sufixo `.SA` para acoes brasileiras**
- Acoes BR: ticker com sufixo `.SA` (ex: `PETR4.SA`). Internacionais sem sufixo.
- **Aplicacao:** `backend/app/services/quotes_service.py`

**Cache local com Parquet para historico de cotacoes**
- Salvar cotacoes em `.parquet` e atualizar apenas incrementalmente.
- **Aplicacao:** Sprint 5 e Sprint 8 (Historico Patrimonial).

---

#### Sprint 10 (Renda Fixa e Tesouro Direto) — referencias

**Tesouro Direto via CSV oficial (B3/Tesouro Nacional)**
- URL: `https://www.tesourodireto.com.br/json/br/com/b3/tesouro/tesouro-direto/1/TesouroDireto_HistoricoTaxaPreco.csv`
- **Aplicacao:** `treasury_service.py`

**Banco Central via `python-bcb` (Selic, IPCA, CDI, cambio, IGPM)**
- Instalacao: `pip install python-bcb`
- **Aplicacao:** Sprint 10 / Sprint 12 (IRPF) / Sprint 5 (cambio PTAX).

---

#### Resumo de dependencias a adicionar nas sprints futuras

| Biblioteca | Sprint | Uso |
|---|---|---|
| `python-bcb` | Sprint 5 / Sprint 10 | Selic, IPCA, CDI, PTAX via Bacen |
| `pyarrow` ou `fastparquet` | Sprint 5 / Sprint 8 | Cache de cotacoes em Parquet |

---

## [Unreleased] - Sprint 3 - 2026-06-15

### Refatoracao (Refactor) — Padronizacao total para AsyncSession

**Contexto:** A auditoria das Sprints 0–2 revelou que `performance_service.py` e `routers/performance.py` ainda usavam `Session` sincrona do SQLAlchemy com o padrao legado `db.query(...).filter(...)`. Isso tornava os endpoints de performance incompativeis com o engine asyncpg e causaria crash em producao ao ser chamado.

---

#### performance_service.py — Migracao completa para AsyncSession
- **Problema:** `calc_asset_performance`, `calc_portfolio_performance` e `_build_monthly_history` recebiam `db: Session` e usavam `db.query().filter().all()` (sincrono).
- **Solucao aplicada:**
  - `from sqlalchemy.orm import Session` removido; substituido por `from sqlalchemy.ext.asyncio import AsyncSession`.
  - `from app.models.asset import Asset` removido (nao era utilizado).
  - Todas as queries migradas para `await db.execute(select(...).where(...))` + `.scalars().all()` ou `.all()`.
  - `_build_monthly_history` tornou-se `async def` com `await db.execute(select(...).group_by(...).order_by(...))`.
  - `calc_portfolio_performance` agora usa `await` na chamada de `_build_monthly_history`.
  - Importacoes desnecessarias de `extract`, `func` mantidas do `sqlalchemy` (usadas no historico mensal).
- **Commit:** `297b7e8b` — refactor(sprint3): migrar performance_service para AsyncSession
- **Status:** Concluido.

#### routers/performance.py — Migracao para AsyncSession
- **Problema:** Router importava `from sqlalchemy.orm import Session` e usava `db: Session = Depends(get_db)`. No endpoint `GET /{ticker}`, fazia `db.query(Asset).filter(Asset.ticker == ...).first()` sincrono.
- **Solucao aplicada:**
  - `from sqlalchemy.orm import Session` removido; substituido por `from sqlalchemy.ext.asyncio import AsyncSession`.
  - `from app.models.asset import Asset` removido.
  - Parametro `db` em ambos os endpoints atualizado para `db: AsyncSession = Depends(get_db)`.
  - Endpoint `GET /{ticker}`: lookup de ativo migrado para `await db.execute(select(Transaction...).where(...).limit(1))` — busca o ticker diretamente nas transacoes da carteira, sem depender da tabela `Asset`.
- **Commit:** `07b896079` — refactor(sprint3): migrar router performance para AsyncSession
- **Status:** Concluido.

---

### Arquivos modificados na Sprint 3

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/performance_service.py` | Migracao Session → AsyncSession | `297b7e8b` |
| `backend/app/routers/performance.py` | Migracao Session → AsyncSession + remocao do Asset lookup sincrono | `07b896079` |

---

### Estado da base apos Sprint 3

**Todos os services e routers do backend usam exclusivamente `AsyncSession`.** Nao existe mais nenhum `from sqlalchemy.orm import Session` ativo em codigo de producao. O sistema esta pronto para as proximas sprints.

---

## [Sprint 2] - 2026-06-15

### Correcao pos-auditoria

#### routers/transactions.py — Validacao de venda nao era executada
- **Solucao:** Helpers async `_calc_current_quantity` e `_validate_sell` integrados diretamente no router. Validacao ativa em `create_transaction` e `update_transaction`.
- **Commit:** `4a4908e7`
- **Status:** Concluido.

### Refatoracao

#### transaction_service.py — Alinhamento com modelo atual
- **Commit:** `c1434e56`
- **Status:** Concluido.

### Testes

#### test_transaction_service.py — Reescrita completa
- **Commit:** `18fbf392`
- **Status:** Concluido.

### Arquivos modificados na Sprint 2

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/transaction_service.py` | Refatoracao completa | `c1434e56` |
| `backend/tests/test_transaction_service.py` | Reescrita dos testes | `18fbf392` |
| `backend/app/routers/transactions.py` | Validacao de venda async integrada | `4a4908e7` |

---

## [Sessao anterior] - 2026-06-14

### Correcoes de bugs

- Resumo: Total Investido incorreto — corrigido
- Resumo: Seletor de carteiras duplicado — removido
- Patrimonio > Tesouro: botao de novo lancamento — removido
- Transacoes: botao "Nova transacao" — removido
- Modal de edicao: unificado em `TransactionModal` com `mode: 'create' | 'edit'`
- Transacoes: reorganizada com grafico de barras mensais + tabelas por classe
- Transacoes: seletor de classe removido dos filtros globais | Commit `5602fae`
- Transacoes: bug de tabela sumindo ao digitar no filtro de grupo | Commit `5602fae`

### Refatoracao de navegacao

- Patrimonio: subpaginas removidas da sidebar, pagina consolidada | Commit `408fa59`

### Arquivos modificados em 14/06/2026

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | Remocao de subpaginas de Patrimonio | `408fa59` |
| `frontend/src/pages/Transacoes.tsx` | Filtros + correcao bug de busca por grupo | `5602fae` |
