# Relatório Técnico de Diagnóstico e Mapeamento de Oportunidades de Melhoria — SGI v2

**Documento:** `docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`  
**Data:** 29 de Outubro de 2026  
**Status:** Oficial / Aprovado para R1  
**Integrity Mode:** Development (Somente Diagnóstico e Documentação — Sem alteração funcional em código)  
**Referência Contratual:** `ORIGINAL_REQUEST.md`, `docs/architecture.md`, `docs/ARCHITECTURE_DOCTOR.md`, `.agents/skills/sgi-development/SKILL.md`

---

## 1. Sumário Executivo do Diagnóstico

O **SGI v2** (Sistema de Gestão de Investimentos) é uma plataforma financeira corporativa multiclasse concebida para consolidação patrimonial, rentabilidade ponderada pelo tempo (TWR), cálculo de direitos e proventos (dividendos, JCP, bonificações, frações), conformidade fiscal (IRPF anual e mensal) e acompanhamento de metas orçamentárias. O sistema opera sobre oito classes centrais de ativos: Ações Brasileiras, Fundos de Investimento Imobiliário (FIIs), Renda Fixa Privada (CDB, LCI, LCA, CRI, CRA, Debêntures), Tesouro Direto, Criptoativos, BDRs, ETFs e Ativos Internacionais.

### 1.1 Princípio Fundamental DB-First
O SGI v2 é rigidamente orientado pelo princípio arquitetural **DB-first**:
1. Todas as consultas, agregações, valuations e apurações financeiras leem **exclusivamente dados persistidos** no banco de dados local (`asset_prices`, `transactions`, `asset_dividends`, `corporate_events`, `rate_history`, `portfolio_snapshots`).
2. Provedores externos de mercado (Brapi, BCB SGS, B3 Cotahist, Tesouro Transparente, CoinGecko) são confinados a rotinas assíncronas isoladas de ingestão, bootstrap ou fechamento diário. Nenhuma requisição HTTP na camada de leitura/apresentação tem permissão para acionar chamadas síncronas a APIs de terceiros.
3. A ausência de cotação ou índice histórico não autoriza adivinhações: o cálculo falha de forma fechada (*fail-closed*), sinalizando cobertura incompleta de benchmark ou ausência de cotação oficial.

### 1.2 Maturidade dos Contratos e Estado Atual do Repositório
A auditoria técnica aprofundada realizada nas camadas de backend (`FastAPI`, `SQLAlchemy 2.0`, `Pydantic v2`, `Alembic`, `APScheduler`, `Redis`), frontend (`React 19`, `TypeScript 6`, `Vite 8`, `Tailwind CSS v4`, `TanStack Query v5`, `Vitest`) e documentação consolidou o seguinte diagnóstico:

- **Robustez dos Gates Centrais:**
  - O catálogo do **Architecture Doctor** (`app.doctor`, invariantes `SGI001` a `SGI015`) está ativo. As 6 regras estáticas (`SGI002`, `SGI004`, `SGI005`, `SGI007`, `SGI009`, `SGI012`) e os contratos comportamentais (`SGI013`, `SGI014`, `SGI015`) passam com 100% de sucesso.
  - A integridade da cadeia do Alembic (66 arquivos de versão, 67 revisões lineares sem bifurcações) está íntegra até a cabeça `20261022_auth_oauth_mfa`.
  - A suíte de testes unitários e de integração do backend possui **2.591 testes coletados**, com **2.584 aprovados, 7 pulados (por ausência de Postgres local e permissões de symlink no Windows) e 0 falhas**.
  - No frontend, o typecheck (`tsc --noEmit`), o linter ESLint e a suíte Vitest (65 arquivos, 258 testes) passam com **zero falhas e zero alertas**.

- **Descompasso Temporal da Documentação (Código à Frente da Documentação):**
  - Recursos completos e entregues em produção estão rotulados em `README.md` e `docs/architecture.md` como "planejado", "backlog pós-GO" ou "parcialmente implementado". Dentre eles: o motor analítico **Analysis Engine (#360)**, a camada de **Inteligência Artificial (#361)**, a autenticação **Google OAuth 2.0 e MFA TOTP (#97)**, a gaveta consolidada de detalhe de ativos **Asset Detail Drawer (#58 / #351)** e os simuladores de carteira (#359).

- **Oportunidades Arquiteturais Identificadas:**
  - Foram catalogadas **19 oportunidades de melhoria técnica**, cobrindo integridade contábil, segurança/autorização, governança de branches, orquestração assíncrona, tolerância a falhas HTTP e experiência de desenvolvimento (DX). Destacam-se o bloqueio de vendas pós-splits por soma bruta na tabela `transactions` (P1) e a finalização da migração do `PortfolioAccessContext` (P1).

---

## 2. Arquitetura e Invariantes Vigentes

O ecossistema SGI v2 é sustentado por contratos formais e invariantes invioláveis. Qualquer proposta de evolução deve respeitar integralmente as seguintes premissas:

```
+------------------------------------------------------------------------------------------------+
|                                    SGI v2 ARQUITETURA GERAL                                   |
+------------------------------------------------------------------------------------------------+
                                                 |
             +-----------------------------------+-----------------------------------+
             |                                                                       |
             v                                                                       v
+--------------------------+                                           +--------------------------+
|       FRONTEND           |                                           |       CORE BACKEND       |
|  React 19.3 / Vite 8.3   |                                           |  FastAPI + Pydantic v2   |
|  Tailwind CSS v4.3       |                                           |  SQLAlchemy 2.0 Async    |
|  TanStack Query v5.104   |                                           |  PostgreSQL 16 + Redis   |
|  Vitest 5.0 (258 testes) |                                           |  APScheduler (Distributed|
+--------------------------+                                           |  Lease TTL 3600-7200s)   |
             |                                                         +--------------------------+
             | REST JSON                                                             |
             | /api/v1/portfolios/{id}/...                                           |
             +-----------------------------------------------------------------------+
                                                 |
                                                 v
                      +-----------------------------------------------------+
                      |         ARQUITETURA DE INVARIANTES (DOCTOR)         |
                      |  SGI001: Alembic/MetaData Drift Gate                |
                      |  SGI002: Rejeição de ORM e Imports Legados          |
                      |  SGI003: Writer Canônico de Transações              |
                      |  SGI004: Writer Único de Snapshots Patrimoniais     |
                      |  SGI005: Dividendos Vinculados ao Ativo Canônico   |
                      |  SGI006: Reconciliação Fail-Closed de Eventos Corp  |
                      |  SGI007: Isolamento DB-first em Leituras Financeiras|
                      |  SGI008: Idempotência do Pipeline de Bootstrap      |
                      |  SGI009: Consumidores Removidos Bloqueados          |
                      |  SGI010: Contratos de Readiness (/ready)            |
                      |  SGI011: Identidade Estrita do Runtime (SHA/Dataset)|
                      |  SGI012: Contrato das Agent Skills                  |
                      |  SGI013: Runtime Determinístico & Clock Canônico    |
                      |  SGI014: Autorização por PortfolioAccessContext     |
                      |  SGI015: Reliable Async Leases Distribuídas (Redis) |
                      +-----------------------------------------------------+
```

### 2.1 Backend: FastAPI, SQLAlchemy 2.0 Async e Alembic
- **Framework Web:** FastAPI assíncrono com validação estrita via Pydantic v2. Rotas expõem envelopes versionados (`.v1`, `.v2`) com prefixo canônico `/api/v1`.
- **Persistência Assíncrona:** SQLAlchemy 2.0 utilizando driver assíncrono `asyncpg`. Consultas de domínio utilizam a sintaxe canônica `select(...)` e `db.execute(...)`.
- **Evolução de Schema:** Alembic gerenciando 67 revisões encadeadas linearmente. Migrações são estritamente unidirecionais, idempotentes e validadas por testes de integridade (`test_alembic_revision_integrity.py`). Cabeça ativa: `20261022_auth_oauth_mfa`.

### 2.2 Invariantes do Architecture Doctor (`SGI001` - `SGI015`)
O módulo `app/doctor/` assegura que degradações de design não entrem na base:
- `SGI001` (Alembic/MetaData): Garante ausência de drift entre modelos ORM e o banco físico.
- `SGI002` / `SGI009`: Proíbe o ressurgimento de classes e tabelas extintas (`GoalAllocation`, `IrpfLoss`, `TreasuryInvestment`, etc.).
- `SGI003` / `SGI004`: Exige ponto único de escrita para transações (`TransactionWriteService`) e snapshots patrimoniais (`PortfolioSnapshotWriterService`).
- `SGI007`: Impede consultas a APIs externas durante a avaliação de rentabilidade e cotações.
- `SGI010` / `SGI011`: Valida que o endpoint `/ready` responda HTTP 503 caso o commit SHA do runtime divirja do certificado para dados reais.
- `SGI013` (Runtime Determinístico): Exige abstração de tempo via `Clock` e restrição de queries N+1 via query budgets.
- `SGI014` (Access Context): Requer transporte do `PortfolioAccessContext` across routers, services e repositories, proibindo IDs inteiros órfãos.
- `SGI015` (Reliable Async): Exige distributed lease via Redis com TTL explícito e fail-closed para rotinas em background.

### 2.3 Clock Canônico (`app.core.clock.Clock`)
- O sistema veda o acoplamento de lógica contábil e apuração de rentabilidade com o relógio do sistema operacional.
- Em produção, injeta-se `SystemClock`; em ambientes de homologação, testes determinísticos e backfills históricos, injeta-se `FrozenClock(freeze_at=...)`.

### 2.4 Autorização Canônica (`PortfolioAccessContext`)
- Nenhuma operação sobre carteira deve confiar cegamente no `portfolio_id` extraído da URL.
- O contexto de acesso deve transitar entre as camadas:
  - Contexto de Usuário: `PortfolioAccessContext.for_user(portfolio_id=..., user_id=...)`, validando ownership e permissão explícita no banco.
  - Contexto de Sistema: `PortfolioAccessContext.for_system(portfolio_id=..., purpose=...)`, exigindo preenchimento mandatório do campo `purpose` para fins de auditoria em tarefas agendadas e rotinas CLI.

### 2.5 Orquestração Assíncrona e Distributed Job Leases
- O agendador `APScheduler` roda em timezone canônico (`America/Sao_Paulo`).
- Cada rotina recorrente é encapsulada pelo context manager `distributed_job_lock(job_name=..., period=..., ttl_seconds=...)`, utilizando chave no Redis. Caso uma réplica do backend já possua a trava, a execução concorrente é descartada de forma limpa e sem contenção.

### 2.6 Frontend: React 19, Vite 8 e Tailwind CSS v4
- **Core:** React 19 (`^19.3.1`), ReactDOM 19, Vite 8 (`^8.3.4`), Tailwind CSS v4 (`^4.3.3`), TypeScript 6 (`^6.0.3`).
- **Gerenciamento de Estado de Servidor:** TanStack Query v5 (`^5.104.4`) com hooks desacoplados (`usePortfolio`, `useTransactions`, `useProventos`, `useIRPF`).
- **Roteamento:** React Router v7 (`^7.18.4`) com raiz canônica em `/carteira/*` e carregamento tardio (`React.lazy`).
- **Visualização de Dados:** Recharts 3 (`^3.10.1`) e Lucide Icons (`^1.59.0`).
- **Qualidade:** Vitest 5 (`^5.0.5`), JSDOM 29, ESLint 10 com regras estritas e zero tolerância a warnings.

---

## 3. Matriz Completa de Oportunidades de Melhoria Mapeadas

A tabela a seguir consolida todas as 19 oportunidades identificadas pela auditoria técnica do repositório, classificadas por ID, Categoria, Prioridade, Complexidade Estimada e Componentes/Arquivos Afetados:

| ID | Título da Oportunidade | Categoria | Prioridade | Complexidade | Arquivos Afetados |
|---|---|---|:---:|:---:|---|
| **OP-01** | Validação de Saldo para Venda Cega a Eventos Corporativos (Splits/Grupamentos) | Funcional / Integridade Contábil | **P1 — Alta** | Média | `backend/app/services/transaction_write_service.py`<br>`backend/app/routers/transactions.py` |
| **OP-02** | Conclusão da Migração de Fronteiras com `PortfolioAccessContext` | Segurança / Autorização | **P1 — Alta** | Média-Alta | `backend/app/routers/proventos.py`<br>`backend/app/routers/irpf.py`<br>`backend/app/routers/rentabilidade.py`<br>`backend/app/core/scheduler.py` |
| **OP-03** | Alinhamento de Branch e Governança do Repositório (`main` vs `stable-15jun`) | Governança / Processo | **P1 — Alta** | Baixa | Repositório Git (Branches e Commits) |
| **OP-04** | Atualização Integral da Documentação Central (READMEs, Arquitetura e Roadmap) | Documentação / Governança | **P1 — Alta** | Média | `README.md`<br>`docs/architecture.md`<br>`docs/DOCUMENTACAO_DO_SISTEMA.md`<br>`ROADMAP.md` |
| **OP-05** | Global Exception Handler no FastAPI para `PortfolioAccessDenied` | Tratamento de Erros / Resiliência | **P2 — Média** | Baixa | `backend/app/main.py`<br>`backend/app/routers/transactions.py`<br>`backend/app/routers/dividends.py` |
| **OP-06** | Injeção Canônica de `Clock` em Serviços Financeiros Críticos | Determinismo / Testabilidade | **P2 — Média** | Média | `backend/app/services/fixed_income_valuation_service.py`<br>`backend/app/services/rentabilidade_kpi_service.py`<br>`backend/app/services/portfolio_analysis_service.py`<br>`backend/app/services/goals_service.py` |
| **OP-07** | Aplicação de `assert_max_queries` em Leituras Financeiras Reais | Desempenho / Prevenção N+1 | **P2 — Média** | Média | `backend/tests/query_budget.py`<br>`backend/tests/test_portfolio_summary_budget.py` (novo) |
| **OP-08** | Correção do Prefixo Duplicado do Router IRPF no Entrypoint da API | Design de API / Limpeza OpenAPI | **P2 — Média** | Baixa | `backend/app/main.py` |
| **OP-09** | Configuração de Regras do Linter Ruff (`ruff.toml` / `pyproject.toml`) | Qualidade de Código / DX | **P2 — Média** | Baixa | `backend/ruff.toml` (novo)<br>`README.md` |
| **OP-10** | Unificação das Superfícies de Proventos (`dividends.py` vs `proventos.py`) | Arquitetura / Limpeza de Débito | **P2 — Média** | Média | `backend/app/routers/dividends.py`<br>`backend/app/routers/proventos.py` |
| **OP-11** | Otimização do Gerenciador de Sessão de Banco para Leituras (`get_db` vs `get_read_db`) | Performance / Robustez BD | **P3 — Baixa** | Baixa | `backend/app/core/database.py` |
| **OP-12** | Substituição de `client.keys()` Bloqueante no Redis por `scan_iter` | Performance / Escalabilidade | **P3 — Baixa** | Baixa | `backend/app/core/cache.py` |
| **OP-13** | Estruturação Progressiva de Repositórios Dedicados para Desacoplar Consultas | Manutenibilidade / Arquitetura | **P3 — Baixa** | Média | `backend/app/repositories/` |
| **OP-14** | Otimização do Pool de Execução dos Testes Vitest no Frontend | Performance de CI / DX | **P3 — Baixa** | Baixa | `frontend/vitest.config.ts` |
| **OP-15** | Criação dos Documentos Entrypoint Faltantes (`frontend/README.md`, `backend/README.md`, `docs/README.md`) | Documentação / Onboarding | **P2 — Média** | Baixa | `frontend/README.md` (novo)<br>`backend/README.md` (novo)<br>`docs/README.md` (novo) |
| **OP-16** | Alinhamento da Cadência do Scheduler e Registro de Jobs Omitidos em Documentação | Documentação / Operações | **P2 — Média** | Baixa | `docs/DOCUMENTACAO_DO_SISTEMA.md` |
| **OP-17** | Saneamento de Referências Quebradas a Módulos Renomeados ou Extintos | Documentação / Integridade | **P2 — Média** | Baixa | `docs/DOCUMENTACAO_DO_SISTEMA.md`<br>`docs/DEVELOPMENT_CONTINUITY.md` |
| **OP-18** | Atualização Formal da Stack Frontend na Documentação (React 19, Vite 8, Tailwind 4) | Documentação / Integridade | **P2 — Média** | Baixa | `docs/DOCUMENTACAO_DO_SISTEMA.md` |
| **OP-19** | Classificação Formal de Relatórios Históricos com Header de Ponto no Tempo | Documentação / Governança | **P3 — Baixa** | Baixa | Documentos históricos em `docs/` |

---

## 4. Detalhamento de Cada Oportunidade de Melhoria

### OP-01: Validação de Saldo para Venda Cega a Eventos Corporativos (Splits/Grupamentos)
- **Categoria:** Funcional / Integridade Contábil
- **Prioridade Recomendada:** **P1 — Alta** (Risco iminente de erro funcional para o usuário)
- **Contexto e Diagnóstico Técnico Detalhado:**
  Ao registrar uma nova transação de venda (`OperationType.sell`), tanto o serviço central de escrita quanto o endpoint HTTP realizam uma validação prévia de custódia disponível para impedir venda a descoberto. O diagnóstico identificou que essa checagem calcula o saldo atual executando uma consulta direta na tabela `transactions`, somando algebricamente as compras (`buy`) e subtraindo as vendas (`sell`). Essa abordagem é completamente cega a eventos corporativos (como desdobramentos/splits, grupamentos/inplits, bonificações em ações e mudanças de ticker).
- **Evidência no Código:**
  1. `backend/app/services/transaction_write_service.py` (linhas 67–88 e 207–213):
     ```python
     async def _current_quantity(db: AsyncSession, portfolio_id: int, ticker: str, asset_type: str) -> float:
         result = await db.execute(
             select(Transaction.operation, Transaction.quantity).where(
                 Transaction.portfolio_id == portfolio_id,
                 func.lower(Transaction.ticker) == ticker.lower(),
                 Transaction.asset_type == asset_type,
             )
         )
         quantity = 0.0
         for operation, value in result.all():
             op = operation.value if isinstance(operation, OperationType) else str(operation)
             if op == OperationType.buy.value:
                 quantity += float(value)
             elif op == OperationType.sell.value:
                 quantity -= float(value)
         return max(quantity, 0.0)
     ```
  2. `backend/app/routers/transactions.py` (linhas 95–140): A função `_calc_current_quantity` e `_validate_sell` repetem rigorosamente a mesma lógica de soma pura.
- **Justificativa e Impacto Técnico/Funcional:**
  Se um investidor comprou 100 ações de uma empresa que subsequentemente passou por um split 1:2 (passando a ter 200 ações econômicas na carteira), ao tentar registrar a venda legítima de 150 ações, o sistema consulta apenas o histórico cru de transações, calcula saldo de 100 ações e aborta a operação com `HTTP 400 Bad Request` (`"Quantidade insuficiente para venda de TICKER. Posicao atual: 100.0000 | Tentativa: 150.0000"`). O usuário é impedido de transacionar ativos que comprovadamente possui.
- **Proposta de Solução Arquitetural:**
  1. No momento da validação de venda em `transaction_write_service.py`, em vez de consultar a tabela crua `transactions`, invocar o motor canônico de projeção de posições (`get_canonical_portfolio_positions` ou `canonical_positions_service`) passando a data da transação como corte temporal.
  2. Esse leitor já processa o histórico de eventos corporativos através do `corporate_action_engine`, devolvendo a quantidade de custódia econômica real e ajustada.
  3. Eliminar a duplicação em `app/routers/transactions.py`, delegando a validação unicamente ao `TransactionWriteService`.
  4. Adicionar teste unitário de regressão cobrindo o ciclo: Compra de 100 ações -> Registro de split 1:2 -> Venda com sucesso de 150 ações.

---

### OP-02: Conclusão da Migração de Fronteiras com `PortfolioAccessContext`
- **Categoria:** Segurança & Autorização / Alinhamento Arquitetural
- **Prioridade Recomendada:** **P1 — Alta** (Fechamento da proteção IDOR e auditoria sistêmica)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A regra do Architecture Doctor `SGI014` estabelece que toda operação que atue sobre uma carteira específica deve transportar um objeto `PortfolioAccessContext`, que assegura ownership explícito para usuários (`for_user`) ou finalidade não-vazia para jobs em background (`for_system`). Embora a infraestrutura esteja plenamente pronta em `app/core/access_context.py` e homologada em `app/routers/dividends.py`, rotas críticas de alto valor financeiro ainda operam recebendo inteiros livres (`portfolio_id: int`), realizando checagens manuais `_assert_owner` ou confiando implicitamente no token.
- **Evidência no Código:**
  1. `backend/app/core/access_context.py`: Definição dos contratos e exceções (`PortfolioAccessDenied`).
  2. `backend/app/routers/proventos.py` (linhas 35, 78, 120): Todos os endpoints (`/summary`, `/distribuicao`, `/historico-mensal`) recebem `portfolio_id: int` e chamam diretamente o service sem construir o contexto.
  3. `backend/app/routers/irpf.py` (linhas 57, 74, 89): Recebe `portfolio_id: int` diretamente.
  4. `backend/app/routers/rentabilidade.py`: Recebe `portfolio_id: int` sem contexto.
  5. `backend/app/core/scheduler.py` (linhas 279, 317): Tarefas de manutenção chamam serviços de carteira sem instanciar `PortfolioAccessContext.for_system(...)`.
  6. `docs/ACCESS_CONTEXT.md` (linhas 61–74): Documenta formalmente o inventário de dívida de migração pendente.
- **Justificativa e Impacto Técnico/Funcional:**
  A ausência do contexto padronizado fragiliza o modelo de segurança (risco de vulnerabilidades IDOR em novos endpoints) e impede o rastreamento uniforme em logs de auditoria (`audit_logs`). Se uma rotina interna invocar um serviço sem passar por um router que faça a checagem manual, o isolamento entre carteiras de usuários distintos é comprometido.
- **Proposta de Solução Arquitetural:**
  1. **Fase 1 (Módulo Proventos):** Alterar os endpoints de `app/routers/proventos.py` para instanciar `context = PortfolioAccessContext.for_user(portfolio_id=portfolio_id, user_id=current_user.id)` e repassar aos serviços `proventos_service.py`.
  2. **Fase 2 (Módulo IRPF):** Fazer os endpoints `/canonical` e `/anos` consumirem `PortfolioAccessContext`.
  3. **Fase 3 (Módulo Rentabilidade & Snapshots):** Adaptar `rentabilidade_kpi_service.py` e `portfolio_snapshot_service.py`.
  4. **Fase 4 (Background Jobs):** Nos jobs do agendador (`scheduler.py`), envelopar chamadas em `PortfolioAccessContext.for_system(portfolio_id=..., purpose="background_nightly_twr_maintenance")`.

---

### OP-03: Alinhamento de Branch e Governança do Repositório (`main` vs `stable-15jun`)
- **Categoria:** Governança e Processo / Alinhamento Arquitetural
- **Prioridade Recomendada:** **P1 — Alta** (Conformidade contratual de release)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A política de governança do SGI v2 estabelece expressamente em `.agents/skills/sgi-development/SKILL.md` e `README.md` que todo desenvolvimento ativo, correções e diagnósticos devem ocorrer obrigatoriamente a partir da branch `stable-15jun`. A branch `main` atua exclusivamente como receptáculo de macroblocos certificados via Pull Request. O diagnóstico apurou que o repositório local está com checkout ativo na branch `main`, no commit `dea616ee20f42906439e123ba614f620c34a0c66` (`feat(proventos): exibir tabela oficial de proventos...`), que se encontra **1 commit à frente de `stable-15jun`**.
- **Evidência no Código:**
  1. `git branch --show-current` -> `main`.
  2. `git log stable-15jun..main --oneline` -> `dea616ee feat(proventos): exibir tabela oficial de proventos com tipo, data com, data pag e valor unitario`.
  3. `.agents/skills/sgi-development/SKILL.md` (linhas 8–11):
     > *"Work from the repository root on stable-15jun. Before editing, compare the local HEAD with origin/stable-15jun, inspect the working tree... Never rewrite published history or develop directly on main."*
  4. `README.md` (linhas 23–24):
     > *"desenvolvimento obrigatório em stable-15jun; main recebe apenas macroblocos certificados via Pull Request;"*
- **Justificativa e Impacto Técnico/Funcional:**
  Operar diretamente na branch `main` quebra os fluxos automatizados de certificação de runtime (`sgi-certification`), que validam a integridade e prontidão para dados reais (`/ready`) amarrados a SHAs estritos. Além disso, novos commits adicionados diretamente em `main` impedem a revisão controlada e a sincronização bidirecional entre branches.
- **Proposta de Solução Arquitetural:**
  1. Executar a sincronização da branch `stable-15jun` via fast-forward ou merge explícito do commit `dea616ee`, unificando os apontadores:
     ```powershell
     git checkout stable-15jun
     git merge --ff-only main
     ```
  2. Manter o checkout de desenvolvimento permanentemente posicionado em `stable-15jun`.
  3. Atualizar a documentação para esclarecer o procedimento de rebaseline caso uma entrega anterior tenha sido depositada na `main`.

---

### OP-04: Atualização Integral da Documentação Central do Sistema
- **Categoria:** Documentação & Alinhamento Arquitetural
- **Prioridade Recomendada:** **P1 — Alta** (Alinhamento mandatório entre especificação e código vivo)
- **Contexto e Diagnóstico Técnico Detalhado:**
  Existe um descompasso temporal significativo no repositório: múltiplos módulos de alta complexidade foram completamente entregues e testados nas últimas semanas, mas a documentação nos arquivos centrais (`README.md`, `docs/architecture.md`, `ROADMAP.md`) permanece congelada nos checkpoints de 16 a 19 de outubro de 2026.
- **Evidência no Código:**
  1. `README.md` (linhas 213–214): Classifica como pendente/planejado:
     - *"Analysis Engine (#360) — motor determinístico de análise de alocação"* -> **Realidade:** 100% implementado em `portfolio_analysis_service.py` e `AnalisePage.tsx`.
     - *"Camada de IA (#361) — análises e Q&A sobre a carteira"* -> **Realidade:** 100% implementado em `portfolio_ai_analysis_service.py` com testes em backend e frontend.
  2. `README.md` (linha 212) e `docs/architecture.md` (linha 192):
     - *"Asset Detail (#58 / #351) — parcialmente implementado"* -> **Realidade:** Concluído via `AssetDetailDrawer.tsx` em todas as tabelas de ativos.
  3. `docs/architecture.md` (linha 299):
     - Classifica Google OAuth 2.0 como backlog futuro (#97) -> **Realidade:** Totalmente implementado no backend (`google_oauth_service.py`, `auth.py`) e frontend (`GoogleCallbackPage.tsx`), com migração `20261022_auth_oauth_mfa`.
  4. `README.md` (linhas 110–111):
     - Registra a cabeça do Alembic como `20261016_corp_ev_effective_date` -> **Realidade:** A cabeça ativa é `20261022_auth_oauth_mfa` (5 migrações adiante).
- **Justificativa e Impacto Técnico/Funcional:**
  Documentação desatualizada induz agentes autônomos e desenvolvedores a projetarem soluções redundantes para problemas já resolvidos, gerando atrito no onboarding e desorientação no planejamento estratégico do projeto.
- **Proposta de Solução Arquitetural:**
  1. Atualizar integralmente o `README.md` e o `docs/architecture.md` promovendo as seções de Analysis Engine (#360), Camada de IA (#361), OAuth (#97) e Asset Detail (#58) para o status de "Implementado e Homologado".
  2. Atualizar a seção de Banco de Dados do `README.md` para indicar a cabeça real do Alembic (`20261022_auth_oauth_mfa`).
  3. Atualizar o `ROADMAP.md` arquivando os épicos entregues e apontando as próximas prioridades reais.

---

### OP-05: Global Exception Handler no FastAPI para `PortfolioAccessDenied`
- **Categoria:** Tratamento de Erros / Resiliência HTTP
- **Prioridade Recomendada:** **P2 — Média** (Robustez da API e limpeza de logs)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A classe `PortfolioAccessDenied` herda de `LookupError` e representa a rejeição de acesso a uma carteira por ausência de permissão ou não pertencimento ao usuário. O `main.py` não registra um manipulador de exceção para esse tipo específico. Como consequência, qualquer endpoint que não capture a exceção manualmente deixa o erro vazar para o manipulador genérico de `Exception`, gerando um log de stack trace com severidade ERROR e respondendo ao cliente com `HTTP 500 Internal Server Error`, mascarando uma recusa legítima de autorização.
- **Evidência no Código:**
  1. `backend/app/core/access_context.py` (linha 14): `class PortfolioAccessDenied(LookupError): ...`
  2. `backend/app/main.py` (linhas 130–141): Existe apenas handler para `RateLimitExceeded` e o genérico para `Exception`:
     ```python
     @app.exception_handler(Exception)
     async def global_exception_handler(request: Request, exc: Exception):
         logger.exception("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
         return JSONResponse(status_code=500, content={"detail": "Erro interno no servidor. Contate o suporte."})
     ```
  3. `backend/app/routers/transactions.py` (linhas 221, 244, 264, 289) e `backend/app/routers/dividends.py` (linhas 27–28): Dezenas de blocos `try ... except PortfolioAccessDenied as exc: raise HTTPException(status_code=404, detail=str(exc))` espalhados manualmente.
- **Justificativa e Impacto Técnico/Funcional:**
  Código boilerplate repetido em múltiplos endpoints e risco constante de que novos desenvolvedores esqueçam o `try/except`, fazendo com que acessos indevidos poluam os alarmes do monitoramento de produção com erros 500 indevidos.
- **Proposta de Solução Arquitetural:**
  1. Adicionar o manipulador centralizado em `backend/app/main.py`:
     ```python
     from app.core.access_context import PortfolioAccessDenied

     @app.exception_handler(PortfolioAccessDenied)
     async def portfolio_access_denied_handler(request: Request, exc: PortfolioAccessDenied):
         return JSONResponse(status_code=404, content={"detail": str(exc)})
     ```
  2. Simplificar os roteadores de endpoints, removendo o boilerplate manual de captura e relançamento de `HTTPException(404)`.

---

### OP-06: Injeção Canônica de `Clock` em Serviços Financeiros Críticos
- **Categoria:** Determinismo de Runtime / Testabilidade
- **Prioridade Recomendada:** **P2 — Média** (Garantia do contrato `SGI013`)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A regra `SGI013` e a especificação `docs/DETERMINISTIC_RUNTIME.md` estabelecem que nenhum cálculo financeiro pode ler o relógio do hardware/sistema operacional sem permitir injeção de dependência. Foram localizadas mais de 35 chamadas diretas a `date.today()` e `datetime.date.today()` em serviços centrais de rentabilidade, valuation e análise patrimonial.
- **Evidência no Código:**
  1. `backend/app/services/fixed_income_valuation_service.py` (linhas 463 e 560):
     `target = target_date or date.today()`
  2. `backend/app/services/rentabilidade_kpi_service.py` (linha 46):
     `today = date.today()`
  3. `backend/app/services/portfolio_analysis_service.py` (linhas 224 e 455):
     `today = datetime.date.today()` e `reference_date=datetime.date.today().isoformat()`
  4. `backend/app/services/goals_service.py` (linha 113):
     `today = date.today()`
  5. `backend/app/services/portfolio_snapshot_canonical_twr_service.py` (linha 80):
     `upper_bound = end_date or date.today()`
- **Justificativa e Impacto Técnico/Funcional:**
  Impossibilita testes de regressão determinísticos de ponta a ponta sem o uso de bibliotecas de monkeypatching global como `freezegun`. Em cenários de apuração contábil retroativa ou simulações temporais no laboratório, os serviços avaliam posições presentes em vez da data solicitada.
- **Proposta de Solução Arquitetural:**
  1. Atualizar a assinatura dos serviços citados para receber `clock: Clock = SYSTEM_CLOCK` (importado de `app.core.clock`).
  2. Substituir `date.today()` por `clock.today()`.
  3. Nos testes unitários correspondentes, instanciar e injetar `FrozenClock(freeze_at=...)`, validando a consistência temporal das respostas.

---

### OP-07: Aplicação de `assert_max_queries` em Leituras Financeiras Reais
- **Categoria:** Desempenho / Prevenção de Regressão N+1
- **Prioridade Recomendada:** **P2 — Média** (Proteção contra degradação de escalabilidade)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O helper `assert_max_queries` vive em `backend/tests/query_budget.py` com o propósito explícito de limitar o número de round-trips ao banco de dados durante requisições de leitura, evitando regressões N+1. Contudo, ele é utilizado exclusivamente em `tests/test_deterministic_runtime_contract.py` (linha 146) sobre queries artificiais de teste (`SELECT 1`), não cobrindo os serviços financeiros reais da aplicação.
- **Evidência no Código:**
  1. `backend/tests/query_budget.py`: Implementação do context manager de auditoria de queries.
  2. `backend/tests/test_deterministic_runtime_contract.py` (linhas 146–160): Único consumidor no repositório.
  3. Serviços críticos como `get_canonical_portfolio_summary`, `get_canonical_portfolio_positions`, `list_transactions_paginated` e `irpf_report_service` não possuem nenhum teto rígido de queries auditado em suíte de teste.
- **Justificativa e Impacto Técnico/Funcional:**
  Sem proteção de orçamento de queries em testes contínuos, qualquer alteração que introduza um `lazy="select"` em relacionamentos ORM ou um loop de busca por ticker causará degradação imperceptível em carteiras pequenas, mas levará a timeouts sob concorrência em produção.
- **Proposta de Solução Arquitetural:**
  1. Criar suíte de testes de integração `tests/test_portfolio_queries_budget.py` cobrindo carteiras sintéticas padrão com 10, 50 e 100 ativos.
  2. Estabelecer orçamentos de queries fixos (ex: `summary` <= 6 queries, `positions` <= 8 queries) utilizando `assert_max_queries`.
  3. Integrar esses testes ao gate do Architecture Doctor (`SGI013`).

---

### OP-08: Correção do Prefixo Duplicado do Router IRPF no Entrypoint da API
- **Categoria:** Design de API / Limpeza OpenAPI
- **Prioridade Recomendada:** **P2 — Média** (Higiene de rota e consistência do contrato OpenAPI)
- **Contexto e Diagnóstico Técnico Detalhado:**
  No arquivo `backend/app/main.py`, o roteador de IRPF (`irpf.router`) é registrado duas vezes com prefixos diferentes. No entanto, as rotas internas de `irpf.py` já declaram o caminho base `/{portfolio_id}/irpf/...`. Com isso, a segunda inclusão gera endpoints duplicados e semanticamente anômalos no catálogo OpenAPI.
- **Evidência no Código:**
  1. `backend/app/main.py` (linhas 214–215):
     ```python
     app.include_router(irpf.router, prefix=f"{PREFIX}/portfolios", tags=["irpf"])
     app.include_router(irpf.router, prefix=f"{PREFIX}/irpf", tags=["irpf"])
     ```
  2. `backend/app/routers/irpf.py` (linhas 57, 74, 89):
     Declarações `@router.get("/{portfolio_id}/irpf/anos")` e `@router.get("/{portfolio_id}/irpf/{year}/canonical")`.
  3. A segunda linha em `main.py` gera a rota: `/api/v1/irpf/{portfolio_id}/irpf/anos`.
  4. O frontend (`src/hooks/useIRPF.ts`) consome unicamente `/api/v1/portfolios/{id}/irpf/...`.
- **Justificativa e Impacto Técnico/Funcional:**
  Poluição desnecessária na especificação OpenAPI Swagger/ReDoc, expondo rotas redundantes que não possuem testes de frontend e aumentam a superfície de manutenção da API.
- **Proposta de Solução Arquitetural:**
  1. Remover a linha 215 de `backend/app/main.py`.
  2. Manter unicamente a inclusão canônica sob `prefix=f"{PREFIX}/portfolios"`.
  3. Assegurar que os testes de contrato em `test_irpf_canonical_endpoint.py` continuem passando sem alterações.

---

### OP-09: Configuração de Regras do Linter Ruff (`ruff.toml` / `pyproject.toml`)
- **Categoria:** Ferramental de Desenvolvimento / DX
- **Prioridade Recomendada:** **P2 — Média** (Padronização e viabilização de comandos documentados)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O `README.md` recomenda aos desenvolvedores executar `python -m ruff check app tests`. Contudo, inexiste qualquer arquivo `ruff.toml` ou seção `[tool.ruff]` no diretório `backend/`. Ao executar o Ruff com as regras padrão, o utilitário emite 1.421 erros devido a regras excessivamente estritas ou incompatíveis com o estilo existente do projeto (ex: ordenação de imports `I001`, formatações de tabela, e preferência por `Decimal(0)` vs `Decimal("0")`).
- **Evidência no Código:**
  1. Execução de `python -m ruff check app` emite 1.421 erros.
  2. `backend/.flake8`: Arquivo existente que documenta as regras reais adotadas pelo projeto (`--max-line-length=120`, ignores específicos para models).
  3. `README.md` (linha 246): Instrui o comando do Ruff sem prover a configuração compatível.
- **Justificativa e Impacto Técnico/Funcional:**
  Desenvolvedores novatos ou ferramentas de CI que tentem executar o linter oficial do README deparam-se com uma avalanche de erros não relacionados ao seu trabalho, gerando frustração e bloqueando fluxos de contribuição.
- **Proposta de Solução Arquitetural:**
  1. Criar o arquivo `backend/ruff.toml` espelhando a política acordada no `.flake8`:
     ```toml
     line-length = 120
     target-version = "py312"
     exclude = [
         "alembic/versions",
         ".venv",
         "__pycache__"
     ]

     [lint]
     select = ["E", "F", "W"]
     ignore = ["E501", "E221"]

     [lint.per-file-ignores]
     "app/models/*" = ["F401", "F821"]
     ```
  2. Ajustar a instrução no `README.md` e testar a execução para assegurar exit code 0.

---

### OP-10: Unificação das Superfícies de Proventos (`dividends.py` vs `proventos.py`)
- **Categoria:** Arquitetura / Limpeza de Débito Técnico
- **Prioridade Recomendada:** **P2 — Média** (Coerência de endpoints de domínio)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O sistema mantém dois roteadores para o domínio de proventos: `app/routers/dividends.py` (contendo unicamente `GET /{portfolio_id}/dividends`, utilizado originalmente como piloto da migração de `PortfolioAccessContext`) e `app/routers/proventos.py` (contendo os endpoints completos `/summary`, `/distribuicao`, `/historico-mensal`, `/`). O frontend consome unicamente `/proventos/*`, de modo que a superfície protegida de `dividends.py` não atende às telas reais da aplicação.
- **Evidência no Código:**
  1. `backend/app/routers/dividends.py` (linhas 15–40): Rota `/{portfolio_id}/dividends`.
  2. `backend/app/routers/proventos.py` (linhas 1–150): Superfície completa consumida por `frontend/src/hooks/useProventos.ts`.
  3. `backend/app/main.py`: Registra ambos os roteadores.
- **Justificativa e Impacto Técnico/Funcional:**
  Manter dois endpoints sobre o mesmo agregador financeiro gera fragmentação documental, duplica testes e induz a manutenções assimétricas, onde novas regras de negócio são aplicadas em um roteador e omitidas no outro.
- **Proposta de Solução Arquitetural:**
  1. Incorporar o `PortfolioAccessContext` em `app/routers/proventos.py` (conforme OP-02).
  2. Marcar `dividends.py` com `deprecated=True` no OpenAPI ou redirecionar internamente para o consolidado de proventos.
  3. Em ciclo posterior, desativar formalmente a rota `/dividends`.

---

### OP-11: Otimização do Gerenciador de Sessão de Banco para Leituras (`get_db` vs `get_read_db`)
- **Categoria:** Performance & Latência / Robustez Transacional
- **Prioridade Recomendada:** **P3 — Baixa** (Otimização de baixo risco)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A dependência `get_db` gerencia o ciclo de vida das sessões assíncronas do SQLAlchemy para os endpoints FastAPI. O bloco `try ... yield ... finally` executa incondicionalmente um `await session.commit()` ao término de cada requisição bem-sucedida, inclusive para requisições puramente de consulta (`GET`).
- **Evidência no Código:**
  1. `backend/app/core/database.py` (linhas 31–41):
     ```python
     async def get_db() -> AsyncGenerator[AsyncSession, None]:
         async with AsyncSessionLocal() as session:
             try:
                 yield session
                 await session.commit()
             except Exception:
                 await session.rollback()
                 raise
             finally:
                 await session.close()
     ```
- **Justificativa e Impacto Técnico/Funcional:**
  Executar um `COMMIT` no PostgreSQL para requisições somente de leitura adiciona latência desnecessária de rede e processamento de transação. Além disso, caso uma leitura inadvertidamente modifique o estado de instâncias ORM na sessão (por exemplo, via efeitos colaterais de cálculo), essas mutações indesejadas serão persistidas no banco.
- **Proposta de Solução Arquitetural:**
  1. Criar uma dependência dedicada `get_read_db()` em `app/core/database.py`:
     ```python
     async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
         async with AsyncSessionLocal() as session:
             try:
                 yield session
             finally:
                 await session.close()
     ```
  2. Aplicar `get_read_db` progressivamente em rotas analíticas e dashboards (ex: `portfolios/summary`, `rentabilidade`, `irpf`).
  3. No `get_db` padrão, verificar se a sessão foi explicitamente modificada antes de invocar `commit()`.

---

### OP-12: Substituição de `client.keys()` Bloqueante no Redis por `scan_iter`
- **Categoria:** Performance & Latência / Escalabilidade Redis
- **Prioridade Recomendada:** **P3 — Baixa** (Mitigação de risco em produção)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A função utilitária `cache_delete_pattern` é utilizada para invalidar chaves de cache agrupadas por padrão textual. A implementação atual utiliza o comando `keys(pattern)` da biblioteca `redis-py`. O comando `KEYS` possui complexidade temporal $O(N)$ (onde $N$ é o número total de chaves do banco de dados) e roda de forma síncrona no single-thread do Redis, bloqueando todas as outras operações enquanto a varredura ocorre.
- **Evidência no Código:**
  1. `backend/app/core/cache.py` (linhas 93–101):
     ```python
     async def cache_delete_pattern(pattern: str) -> None:
         client = await get_redis()
         if not client:
             return
         try:
             keys = await client.keys(pattern)
             if keys:
                 await client.delete(*keys)
     ```
- **Justificativa e Impacto Técnico/Funcional:**
  Em ambiente de produção com dezenas de milhares de chaves cacheadas (cotações, snapshots, históricos), a invocação de `KEYS` pode gerar picos de latência (spikes) de centenas de milissegundos, provocando timeouts em endpoints concorrentes.
- **Proposta de Solução Arquitetural:**
  1. Refatorar `cache_delete_pattern` em `app/core/cache.py` para utilizar o cursor não bloqueante `scan_iter`:
     ```python
     async def cache_delete_pattern(pattern: str) -> None:
         client = await get_redis()
         if not client:
             return
         try:
             keys_to_delete = []
             async for key in client.scan_iter(match=pattern, count=100):
                 keys_to_delete.append(key)
             if keys_to_delete:
                 await client.delete(*keys_to_delete)
         except Exception as exc:
             logger.warning("Falha ao excluir cache pattern=%s: %s", sanitize_log_value(pattern), exc)
     ```

---

### OP-13: Estruturação Progressiva de Repositórios Dedicados para Desacoplar Consultas
- **Categoria:** Manutenibilidade / Arquitetura de Software
- **Prioridade Recomendada:** **P3 — Baixa** (Evolução arquitetural contínua)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O diretório `backend/app/repositories/` foi criado para isolar o acesso ao banco de dados e conter queries complexas do SQLAlchemy, mas atualmente conta com apenas um único arquivo: `portfolio_access_repository.py`. Os mais de 230 serviços sob `backend/app/services/` montam e executam queries SQL diretamente via `db.execute(select(...))`.
- **Evidência no Código:**
  1. `backend/app/repositories/portfolio_access_repository.py`: Único repositório presente.
  2. Serviços como `canonical_positions_service.py`, `rentabilidade_kpi_service.py` e `transaction_write_service.py` misturam regras de negócio financeiras com lógica de junção de tabelas e cláusulas `where`.
- **Justificativa e Impacto Técnico/Funcional:**
  Dificulta testes unitários puros (sem banco de dados SQLite/Postgres em memória) e gera duplicação de queries idênticas entre diferentes serviços (ex: busca de cotações recentes ou checagem de ativos no catálogo).
- **Proposta de Solução Arquitetural:**
  1. Criar repositórios de domínio focados sob demanda: `AssetRepository`, `TransactionRepository`, `CorporateEventRepository`.
  2. Migrar progressivamente as chamadas repetitivas de queries dos serviços para esses repositórios, injetando-os via dependências FastAPI.

---

### OP-14: Otimização do Pool de Execução dos Testes Vitest no Frontend
- **Categoria:** Experiência do Desenvolvedor / Desempenho de CI
- **Prioridade Recomendada:** **P3 — Baixa** (Ganho de produtividade no ciclo local)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A execução da suíte Vitest no frontend (`npm test -- --run`) leva aproximadamente 155 a 160 segundos no Windows para rodar 258 testes em 65 arquivos. O profiler do próprio Vitest emite o diagnóstico informando que o ambiente virtual `jsdom` é destruído e recriado 65 vezes, consumindo 469 segundos cumulativos de CPU (47% do tempo total medido).
- **Evidência no Código:**
  1. Log da execução do Vitest:
     > *"Environment jsdom was created 65 times · 469.33s total, 47% of tracked time. create it once per worker with pool: 'vmThreads' (keeps per-file isolation) or isolate: false"*
  2. `frontend/vitest.config.ts`: Configuração com pool padrão por processo sem reutilização de workers JSDOM.
- **Justificativa e Impacto Técnico/Funcional:**
  O tempo excessivo de execução dos testes locais retarda o ciclo de feedback rápido (*edit-test loop*) para desenvolvedores e encarece o pipeline de CI no GitHub Actions.
- **Proposta de Solução Arquitetural:**
  1. Testar em branch experimental a adição de `pool: 'vmThreads'` ou `isolate: false` no `vitest.config.ts`.
  2. Assegurar que nenhum teste dependa de estado residual no DOM ou em mocks globais.
  3. Reduzir o tempo de execução local de ~160s para ~40s preservando a integridade das 258 asserções.

---

### OP-15: Criação dos Documentos Entrypoint Faltantes (`frontend/README.md`, `backend/README.md`, `docs/README.md`)
- **Categoria:** Documentação / Onboarding
- **Prioridade Recomendada:** **P2 — Média** (Higiene de repositório e facilidade de navegação)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A auditoria do inventário de documentação (`spec_miner_survey_1`) constatou que, embora existam 156 arquivos `.md` detalhados no repositório, inexistem arquivos `README.md` específicos nas raízes de `frontend/` e `backend/`, bem como inexiste um índice estruturado em `docs/README.md`.
- **Evidência no Código:**
  1. `frontend/README.md` -> Inexistente.
  2. `backend/README.md` -> Inexistente.
  3. `docs/README.md` -> Inexistente (a pasta `docs/` possui 70 arquivos na raiz sem índice mestre navegável).
- **Justificativa e Impacto Técnico/Funcional:**
  Desenvolvedores frontend ou backend que clonam o repositório ou navegam pelas pastas no GitHub ficam sem uma visão rápida e contextualizada sobre como rodar, testar e configurar cada subprojeto isoladamente.
- **Proposta de Solução Arquitetural:**
  1. Redigir `backend/README.md` com arquitetura FastAPI, ambiente Python/`.venv`, execução do Doctor e suíte de testes.
  2. Redigir `frontend/README.md` com stack React 19/Vite 8, scripts npm (`typecheck`, `lint`, `test`, `build`) e convenções de rotas `/carteira`.
  3. Redigir `docs/README.md` funcionando como catálogo/índice temático categorizando todos os documentos por domínio (Arquitetura, IRPF, Proventos, Eventos Corporativos, Mercado, Operações, Histórico).

---

### OP-16: Alinhamento da Cadência do Background Scheduler e Registro de Jobs Omitidos
- **Categoria:** Documentação & Operações / Governança do Scheduler
- **Prioridade Recomendada:** **P2 — Média** (Precisão operacional e auditoria)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O arquivo `docs/DOCUMENTACAO_DO_SISTEMA.md` descreve a rotina de tarefas agendadas de forma simplificada e desatualizada (mencionando cadência de cotações a cada 30 minutos e horários genéricos), omitindo jobs recorrentes de grande relevância criados em revisões recentes.
- **Evidência no Código:**
  1. `backend/app/core/scheduler.py`:
     - Cotações intraday: Cadência de 90 minutos em dias úteis (09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00) com lock de 7200s (linhas 21–57).
     - Fechamento diário de ações/FIIs: 20:45 BRT (linhas 98–146).
     - Sincronização de CDI/Selic/IPCA: 20:40 BRT (linhas 150–177).
     - Sincronização de fechamento IBOV: 20:42 BRT (linhas 179–203).
     - Fechamento do Tesouro Direto: 20:50 BRT (linhas 205–235).
     - **Notificação matinal de dividendos:** 08:30 BRT (`notify_daily_dividend_payments`, linhas 237–268) — **Completamente omitido em docs!**
     - Manutenção automática de snapshots/TWR: 21:00 BRT (linhas 270–301).
     - **Atualização diária de indicadores fundamentalistas e IA:** 21:30 BRT (`refresh_asset_fundamentals_daily`, linhas 303–337) — **Completamente omitido em docs!**
     - **Auditoria mensal da fonte oficial da B3:** Dia 1 às 08:15 BRT (`audit_b3_market_calendar_monthly`, linhas 340–390) — **Completamente omitido em docs!**
  2. `docs/DOCUMENTACAO_DO_SISTEMA.md` (linhas 125–132): Horários e jobs não coincidem com o código implementado.
- **Justificativa e Impacto Técnico/Funcional:**
  Operadores e equipes de SRE tomam decisões incorretas de dimensionamento e monitoramento por desconhecerem os horários e o impacto das tarefas em background no banco de dados e no Redis.
- **Proposta de Solução Arquitetural:**
  1. Atualizar a Seção 4 de `docs/DOCUMENTACAO_DO_SISTEMA.md` e `docs/operations.md` detalhando a tabela exata com Job ID, Expressão Cron, Horário BRT, Flag de Ativação e TTL do Distributed Lock.

---

### OP-17: Saneamento de Referências Quebradas a Módulos Renomeados ou Extintos
- **Categoria:** Documentação / Integridade de Links
- **Prioridade Recomendada:** **P2 — Média** (Eliminação de confusão técnica)
- **Contexto e Diagnóstico Técnico Detalhado:**
  A varredura estática de caminhos inline e citações em backticks identificou 34 referências a scripts e módulos que foram renomeados ou eliminados durante refatorações anteriores.
- **Evidência no Código:**
  1. `docs/DOCUMENTACAO_DO_SISTEMA.md` (linha 156): Cita `backend/app/integrations/cotahist.py`. O arquivo real é `backend/app/integrations/b3_cotahist.py`.
  2. `docs/DEVELOPMENT_CONTINUITY.md` e `docs/USER_TEST_STACK.md`: Cita `docker-compose.usertest.yml`, arquivo que foi descontinuado e não existe no repositório.
  3. Citações a scripts utilitários antigos de Tesouro renomeados durante a unificação de catálogo.
- **Justificativa e Impacto Técnico/Funcional:**
  Desenvolvedores e scripts de automação falham ao tentar inspecionar arquivos inexistentes citados em manuais de operação e runbooks.
- **Proposta de Solução Arquitetural:**
  1. Fazer varredura de substituição textual em `docs/` corrigindo as citações apontadas para os arquivos vigentes.

---

### OP-18: Atualização Formal da Stack Frontend na Documentação
- **Categoria:** Documentação / Integridade Técnica
- **Prioridade Recomendada:** **P2 — Média** (Acurácia técnica)
- **Contexto e Diagnóstico Técnico Detalhado:**
  O arquivo `docs/DOCUMENTACAO_DO_SISTEMA.md` afirma que o frontend utiliza "React 18, TypeScript 5, Vite 5, Tailwind CSS 3". O `package.json` real do projeto demonstra que a stack foi modernizada para componentes de última geração.
- **Evidência no Código:**
  1. `docs/DOCUMENTACAO_DO_SISTEMA.md` (linha 164): Afirma versão legada.
  2. `frontend/package.json`:
     - `"react": "^19.3.1"` (React 19)
     - `"vite": "^8.3.4"` (Vite 8)
     - `"tailwindcss": "^4.3.3"` (Tailwind CSS v4)
     - `"typescript": "^6.0.3"` (TypeScript 6)
     - `"@tanstack/react-query": "^5.104.4"` (React Query v5)
- **Justificativa e Impacto Técnico/Funcional:**
  Inconsistência técnica em documentações de arquitetura, gerando dúvidas sobre a compatibilidade de novas bibliotecas de UI e plugins do Vite.
- **Proposta de Solução Arquitetural:**
  1. Atualizar todas as menções da stack frontend nos documentos oficiais para refletir React 19, Vite 8, Tailwind CSS v4, TypeScript 6 e TanStack Query v5.

---

### OP-19: Classificação Formal de Relatórios Históricos com Header de Ponto no Tempo
- **Categoria:** Documentação / Governança de Contratos
- **Prioridade Recomendada:** **P3 — Baixa** (Higiene e rastreabilidade histórica)
- **Contexto e Diagnóstico Técnico Detalhado:**
  Aproximadamente 45 documentos no diretório `docs/` foram gerados como auditorias pontuais ou registros de decisão de migração de versões antigas (ex: `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md`, `docs/ALEMBIC_CONSUMER_INVENTORY_2026-08.md`, `docs/ARCHITECTURAL_REVIEW_2026-07-23.md`). Muitos leitores não conseguem distinguir se esses documentos representam a especificação viva atual ou o registro histórico de um momento passado.
- **Evidência no Código:**
  1. Arquivos com sufixo `2026-07`, `2026-08`, `2026-09` e `2026-10-16` em `docs/`.
  2. Citações a tabelas e campos já eliminados que eram verdadeiros na data da redação daqueles relatórios.
- **Justificativa e Impacto Técnico/Funcional:**
  Sem um cabeçalho claro, novos contribuidores e auditores tratam registros históricos como documentação viva desatualizada e tentam alterar fatos históricos.
- **Proposta de Solução Arquitetural:**
  1. Preservar integralmente o conteúdo original dos documentos históricos.
  2. Adicionar no topo de cada documento um **Historical Checkpoint Header**:
     ```markdown
     > **Nota Histórica de Ponto no Tempo**: Este documento é um registro de auditoria realizado em [Data].
     > Para as especificações e contratos vigentes do SGI v2, consulte `README.md` e `docs/architecture.md`.
     ```

---

## 5. Plano de Execução e Roadmap Sugerido de Implementação

Para viabilizar a execução ordenada dessas oportunidades sem gerar disrupções nos testes vigentes nem violar a governança de branches, propõe-se um roadmap estruturado em quatro fases sequenciais:

```
+-----------------------------------------------------------------------------------------------+
|                       ROADMAP SUGERIDO DE EXECUÇÃO (RODADAS FUTURAS)                          |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
| FASE 1: Governança, Documentação Integral & Melhorias Canônicas [CONCLUÍDA - PR #453]        |
| - OP-03: Governança em stable-15jun e PR formal para main.                                    |
| - OP-04 / OP-15 / OP-16 / OP-17 / OP-18 / OP-19: Documentação integral e novos manuais.       |
| - OP-01: Validação de venda de ativos com suporte a splits em transaction_write_service.      |
| - OP-02 (Parcial): PortfolioAccessContext em proventos.py com get_accessible_portfolio.       |
| - OP-05: Global Exception Handler para PortfolioAccessDenied no FastAPI (HTTP 404).           |
| - OP-06 (Parcial): Injeção de Clock canônico em FixedIncome e Goals.                          |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
| FASE 2: Segurança Canônica e Unificação de Superfícies [CONCLUÍDA]                            |
| - OP-02 (Conclusão): PortfolioAccessContext em irpf.py, rentabilidade.py e jobs (scheduler). |
| - OP-10: Unificação de superfícies de proventos: dividends.py marcado como deprecated.        |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
| FASE 3: Runtime Determinístico, Qualidade e Ferramental DX                                    |
| - OP-06: Injetar Clock em fixed_income_valuation, rentabilidade_kpi, portfolio_analysis.       |
| - OP-07: Criar testes com assert_max_queries para leituras financeiras reais (SGI013).         |
| - OP-09: Criar backend/ruff.toml alinhado com .flake8 e validar no README.                    |
| - OP-10: Unificar endpoints de dividends e proventos com depreciação controlada.             |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
| FASE 4: Otimização de Performance, Escalabilidade e Manutenibilidade                          |
| - OP-11: Introduzir get_read_db() sem commit automático em leituras puras.                   |
| - OP-12: Migrar cache_delete_pattern de Redis KEYS para scan_iter assíncrono.                 |
| - OP-14: Ajustar pool Vitest (vmThreads / isolate: false) para acelerar testes frontend.     |
| - OP-13: Estruturar repositórios dedicados para queries recorrentes em app/repositories/.      |
+-----------------------------------------------------------------------------------------------+
```

---

## 6. Conformidade e Validação Local

Todas as evidências, contratos e testes citados neste diagnóstico podem ser verificados de forma 100% autônoma, local e reprodutível no ambiente de desenvolvimento Windows/PowerShell, sem dependência de serviços externos ou escritas em produção:

### 6.1 Verificação Rápida do Architecture Doctor (< 20 segundos)
```powershell
cd backend
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
```
- **Resultado Esperado:** Exit code `0`, JSON com schema `architecture-doctor.v1`, 6 regras estáticas com status `pass` (`SGI002`, `SGI004`, `SGI005`, `SGI007`, `SGI009`, `SGI012`).

### 6.2 Verificação de Integridade das Migrações e Contratos Centrais (< 10 segundos)
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_alembic_revision_integrity.py tests/test_deterministic_runtime_contract.py tests/test_portfolio_access_context.py tests/test_distributed_job_lock.py -q
```
- **Resultado Esperado:** 24 testes aprovados (`24 passed`), exit code `0`.

### 6.3 Verificação de Contratos de Documentação no Pytest (< 10 segundos)
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_agent_skills_contract.py tests/test_architecture_doctor_catalog.py tests/test_dividends_canonical_docs.py tests/test_portfolio_snapshot_single_writer_policy.py -q
```
- **Resultado Esperado:** Todos os testes de compliance de documentação aprovados, exit code `0`.

### 6.4 Verificação Completa do Frontend (< 4 minutos)
```powershell
cd frontend
npm run typecheck
npm run lint
npm test -- --run
npm run build
```
- **Resultado Esperado:** `tsc --noEmit` limpo, ESLint com 0 erros/warnings, Vitest com 65 arquivos e 258 testes aprovados, build em `dist/` gerado com sucesso.

### 6.5 Verificação da Branch Git
```powershell
git status
git branch --show-current
git log stable-15jun..main --oneline
```
- **Resultado Esperado:** Identificação do checkout atual e confirmação da divergência de 1 commit documentada em OP-03.

---

*Fim do Relatório Técnico de Diagnóstico e Mapeamento de Oportunidades de Melhoria — SGI v2.*
