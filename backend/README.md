# SGI v2 — Backend (FastAPI Core)

Guia técnico, arquitetural e operacional do backend do **SGI v2 (Sistema de Gestão de Investimentos)**.

> **Documentação Central do Sistema:** Consulte [`docs/DOCUMENTACAO_DO_SISTEMA.md`](../docs/DOCUMENTACAO_DO_SISTEMA.md).
> **Relatório Oficial de Oportunidades de Melhoria:** Consulte [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](../docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md).

---

## 1. Visão Geral da Arquitetura

O backend do SGI v2 é construído sobre Python 3.12+ utilizando **FastAPI**, **SQLAlchemy 2.0 (assíncrono)**, **Pydantic v2**, **Alembic**, **PostgreSQL 16** e **Redis**. Ele provê a API RESTful corporativa, a execução determinística de regras contábeis, cálculo de rentabilidade ponderada pelo tempo (TWR), controle de proventos sob demanda, apuração fiscal de IRPF e orquestração assíncrona com travas distribuídas.

### Estrutura de Diretórios

```text
backend/
├── alembic/                # Scripts de migração de banco de dados (Alembic)
│   └── versions/           # 67 revisões lineares (head: 20261022_auth_oauth_mfa)
├── app/                    # Código-fonte principal da aplicação
│   ├── cli/                # 64 módulos de linha de comando operacionais e administrativos
│   ├── core/               # Configurações, segurança, database, redis, clock e scheduler
│   ├── doctor/             # Architecture Doctor (regras estáticas e contratos SGI001–SGI015)
│   ├── integrations/       # Clientes de provedores externos (BCB SGS, B3 Cotahist, Brapi, etc.)
│   ├── models/             # Modelos declarativos ORM SQLAlchemy 2.0
│   ├── repositories/       # Camada de abstração e persistência de dados
│   ├── routers/            # Controladores REST FastAPI organizados por domínio
│   ├── schemas/            # Contratos de DTO e validação estrita com Pydantic v2
│   └── services/           # Regras de negócio, projeção canônica, valuation e cálculos fiscais
├── tests/                  # Suíte de testes automatizados Pytest (> 2.500 testes)
├── Dockerfile              # Imagem de produção Python 3.12 Slim
├── requirements.txt        # Dependências de execução
├── requirements-test.txt   # Dependências exclusivas de teste e qualidade
└── setup.cfg / .flake8     # Configurações de linters e ferramentas
```

---

## 2. Invariantes Arquiteturais Centrais

O desenvolvimento no backend do SGI v2 é rigidamente condicionado pelos seguintes princípios e contratos:

### 2.1 Princípio DB-First
- Todos os endpoints de leitura (`GET /api/v1/...`), cálculos de rentabilidade, consolidação patrimonial, proventos e IRPF leem **exclusivamente dados persistidos** no PostgreSQL local (`asset_prices`, `transactions`, `asset_dividends`, `corporate_events`, `rate_history`, `portfolio_snapshots`).
- Provedores externos de mercado (Brapi, BCB SGS, Tesouro Transparente, CoinGecko, B3 Cotahist) são confinados a rotinas assíncronas isoladas de sincronização diária ou bootstrap. Nenhuma requisição HTTP na rota de apresentação pode invocar APIs de terceiros.
- Ausência de cotação ou taxa não é convertida em zero, paridade fixa ou estimativa não auditada: o sistema adota comportamento estritamente **fail-closed**.

### 2.2 Relógio Canônico e Determinismo (`Clock`)
- Lógicas contábeis e financeiras sensíveis a datas injetam a abstração `app.core.clock.Clock`.
- Em produção, injeta-se `SystemClock` (horário operacional `America/Sao_Paulo`).
- Em testes automatizados, homologação e backfills históricos, injeta-se `FrozenClock(freeze_at=...)`, assegurando reprodutibilidade temporal total.

### 2.3 Autorização por Escopo Explícito (`PortfolioAccessContext`)
- Nenhum identificador numérico de carteira (`portfolio_id`) recebido da URL é tratado como autoridade.
- As chamadas entre routers, services e repositories devem transitar o contexto:
  - **Contexto de Usuário:** `PortfolioAccessContext.for_user(portfolio_id=..., user_id=...)`, validando ownership e permissão explícita na persistência.
  - **Contexto de Sistema:** `PortfolioAccessContext.for_system(portfolio_id=..., purpose=...)`, exigindo preenchimento obrigatório da finalidade auditável para tarefas agendadas e rotinas CLI. Bypass implícito é proibido.

### 2.4 Ponto Único Canônico de Escrita (Single Writer Policy)
- **Transações:** Apenas o `TransactionWriteService` possui autoridade para persistir lançamentos contábeis na tabela `transactions`. A tabela `transactions` é o livro-razão canônico de todas as classes (ações, FIIs, renda fixa, tesouro, cripto).
- **Snapshots Patrimoniais:** Apenas o `PortfolioSnapshotWriterService` (`portfolio_snapshot_canonical_twr_service.py`) é autorizado a materializar snapshots patrimoniais e classes em `portfolio_snapshots` e `portfolio_class_snapshots`.

### 2.5 Travas Distribuídas com Fail-Closed (`distributed_job_lock`)
- Tarefas agendadas globais no APScheduler utilizam o context manager `distributed_job_lock(job_name=..., period=..., ttl_seconds=...)` sobre chaves no Redis.
- Em ambientes com múltiplos nós ou workers, contention é resolvida descartando a execução concorrente de forma segura e sem gerar conflitos no banco de dados.

### 2.6 Budgets de Queries (`assert_max_queries`)
- Leituras financeiras de alta frequência são protegidas contra regressões N+1 por tetos estritos de queries SQL (`assert_max_queries`), garantindo que novas relações não degradem o pool de conexões.

---

## 3. Banco de Dados e Governança de Migrations (Alembic)

- **Engine Assíncrono:** Conexões gerenciadas via SQLAlchemy 2.0 com driver `asyncpg` sobre PostgreSQL 16.
- **Sessões:** Injetadas via dependência `get_db` no FastAPI utilizando context manager assíncrono `AsyncSessionLocal()`.
- **Governança Alembic:** Todas as alterações no schema DDL são estritamente unidirecionais e encadeadas de forma linear em `backend/alembic/versions/`.
- **Cabeça Vigente:** `20261022_auth_oauth_mfa` (67 revisões encadeadas sem ramificações abertas).
- **Gate de Drift:** O teste `tests/test_alembic_drift_gate.py` valida periodicamente a paridade perfeita entre os modelos SQLAlchemy `MetaData` e as revisões do Alembic.

---

## 4. Architecture Doctor (`app.doctor`)

O módulo `backend/app/doctor` é o sistema interno de inspeção e validação de invariantes arquiteturais do SGI v2. Ele implementa verificações automatizadas para 15 regras (`SGI001` a `SGI015`), incluindo rejeição de imports legados, writer único de snapshots, contratos de skills de IA, isolamento DB-first e integridade de readiness.

Para executar todas as regras estáticas com emissão de relatório padronizado:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
```

O comando deve retornar `exit_code: 0` com todas as regras estáticas aprovadas (`pass`).

---

## 5. Rotinas em Segundo Plano (Scheduler)

Configurado em `backend/app/core/scheduler.py` via APScheduler no fuso horário `America/Sao_Paulo`:

| Horário (BRT) | ID do Job | Finalidade | Bloqueio / Lock |
| :--- | :--- | :--- | :--- |
| **09h–18h (a cada 90m)** | `update_quotes_intraday_*` | Atualiza cotações correntes dos ativos em negociação | Redis lock (TTL 7200s) |
| **08:30 (dias úteis)** | `notify_daily_dividend_payments` | Dispara resumo matinal por e-mail dos proventos pagos no dia | Redis lock (TTL 3600s) |
| **20:40 (dias úteis)** | `sync_benchmark_rates_daily` | Sincroniza CDI, Selic, IPCA e IGPM via BCB SGS com anti-WAF | Redis lock (TTL 3600s) |
| **20:42 (dias úteis)** | `sync_ibov_benchmark_daily` | Sincroniza fechamento e calcula retorno diário do Ibovespa | Redis lock (TTL 3600s) |
| **20:45 (dias úteis)** | `persist_daily_close_prices` | Grava fechamento oficial diário de todos os ativos sob custódia | Redis lock (TTL 7200s) |
| **20:50 (dias úteis)** | `persist_treasury_daily_close` | Sincroniza fechamento diário de preços e taxas do Tesouro Direto | Redis lock (TTL 7200s) |
| **21:00 (dias úteis)** | `portfolio_snapshot_auto_maintenance` | Consolidação patrimonial diária e cálculo de rentabilidade TWR | Redis lock (TTL 7200s) |
| **21:30 (dias úteis)** | `refresh_asset_fundamentals_daily` | Atualiza indicadores fundamentalistas e consenso de mercado | Redis lock (TTL 7200s) |
| **Dia 01 às 08:15** | `audit_b3_market_calendar_monthly` | Auditoria read-only da fonte oficial do calendário da B3 | Redis lock (TTL 300s) |

---

## 6. Ferramentas Administrativas e Linha de Comando (CLI)

O diretório `backend/app/cli/` contém 64 utilitários especializados para operações de suporte, migração e auditoria. Exemplos de utilitários centrais:
- `app.cli.system_bootstrap`: Inicialização e carga inicial canônica multi-provedor de ativos, cotações e benchmarks.
- `app.cli.irpf_annual_assessment`: Apuração anual consolidada de imposto de renda da carteira.
- `app.cli.real_data_certification`: Validação formal e persistência append-only de certificados para dados reais.
- `app.cli.user_test_readiness`: Inspeção estática e funcional de prontidão operacional (`GO_ASSISTED`).
- `app.cli.cleanup_empty_treasury_duplicate_assets`: Saneamento de duplicidades históricas de títulos públicos.

---

## 7. Comandos de Validação e Desenvolvimento Local

As ferramentas abaixo devem ser executadas no ambiente virtual local (`.venv`):

### 7.1 Execução de Testes Automatizados (Pytest)

```powershell
# Executar a suíte completa de testes do backend
cd backend
..\.venv\Scripts\python.exe -m pytest tests/ -q --tb=line --disable-warnings

# Executar testes focados de contratos e arquitetura
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_agent_skills_contract.py tests/test_architecture_doctor_catalog.py tests/test_dividends_canonical_docs.py tests/test_portfolio_snapshot_single_writer_policy.py -q
```

### 7.2 Análise Estática e Tipagem (Mypy)

```powershell
cd backend
..\.venv\Scripts\python.exe -m mypy app
```

### 7.3 Padronização de Código e Linting (Flake8)

No Windows e em alinhamento com os parâmetros oficiais de CI (`.github/workflows/ci.yml`), execute o Flake8 com limite de 120 caracteres e processamento em job único (`--jobs=1`):

```powershell
cd backend
..\.venv\Scripts\python.exe -m flake8 app --max-line-length=120 --extend-ignore=E501,E221 --per-file-ignores="app/models/*.py:F821,F401" --jobs=1
```

> **Nota sobre o Ruff:** O arquivo de configuração canônico `backend/ruff.toml` está ativo e espelha integralmente a política do `.flake8`. Para linting ultrarrápido em desenvolvimento local ou no pre-commit, execute:
> ```powershell
> cd backend
> ..\.venv\Scripts\python.exe -m ruff check app tests
> ```

### 7.4 Compilação de Bytecode

```powershell
cd backend
..\.venv\Scripts\python.exe -m compileall -q app tests
```

---

## 8. Governança de Branches e Modelo de Release

O desenvolvimento do backend do SGI v2 é rigidamente condicionado pela política de branches e governança do repositório:

- **Branch Mandatória de Desenvolvimento (`stable-15jun`):**
  - A branch `stable-15jun` é a **única branch permitida** para desenvolvimento contínuo, integração, testes e homologação de código.
  - Todas as ramificações locais de trabalho (`feature/*`, `fix/*`, `chore/*`) e commits locais devem obrigatoriamente ter como base e destino final de integração a branch `stable-15jun`.
  - Antes de sincronizar alterações via `git push origin stable-15jun`, é compulsório validar a integridade local com a suíte de testes (`pytest tests/`), o Architecture Doctor (`python -m app.doctor --all-static --format json`) e os linters configurados (`flake8 app`).

- **Branch de Produção (`main`):**
  - A branch `main` espelha fielmente o ambiente de produção e o estado homologado com dados reais certificados.
  - O código em `main` é promovido **exclusivamente** a partir de macroblocos validados em `stable-15jun` por meio de Pull Requests formais, auditadas e com certificação verificável de integridade (SHA e dataset de produção).
  - **É terminantemente proibido efetuar `git push` direto para a branch `main`**. O desenvolvimento direto em `main` invalida garantias de auditoria, a identidade de runtime (`/ready`) e a conformidade corporativa.

Para aprofundamento das regras de governança e garantia pré-commit, consulte [`docs/DOCUMENTACAO_DO_SISTEMA.md`](../docs/DOCUMENTACAO_DO_SISTEMA.md#8-governança-e-ciclo-de-desenvolvimento).

---

## 9. Referências e Documentos Correlatos

- [`docs/DOCUMENTACAO_DO_SISTEMA.md`](../docs/DOCUMENTACAO_DO_SISTEMA.md) — Manual unificado do sistema.
- [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](../docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) — Diagnóstico detalhado de oportunidades e prioridades.
- [`docs/architecture.md`](../docs/architecture.md) — Fronteiras, módulos e princípios de design.
- [`docs/ARCHITECTURE_DOCTOR.md`](../docs/ARCHITECTURE_DOCTOR.md) — Especificação completa das regras do Architecture Doctor.
- [`backend/TESTING.md`](TESTING.md) — Guia detalhado de infraestrutura de testes unitários e de integração.
