# SGI — Sistema de Gestão de Investimentos

> **Documentação Completa da Aplicação:** Consulte o manual técnico unificado em [`docs/DOCUMENTACAO_DO_SISTEMA.md`](docs/DOCUMENTACAO_DO_SISTEMA.md).
> **Roadmap vivo:** [`docs/ROADMAP.md`](docs/ROADMAP.md).
> **Guias Técnicos Dedicados:** Backend em [`backend/README.md`](backend/README.md) | Frontend em [`frontend/README.md`](frontend/README.md).
>
> ⚠️ **Regra Obrigatória de Documentação Contínua e Viva:** A cada nova instrução, implementação, correção de bug, refatoração, migração ou criação de recurso/rota no código, **toda a documentação afetada DEVE ser atualizada obrigatoriamente no mesmo bloco de trabalho** (incluindo `README.md`, `docs/ROADMAP.md`, `docs/DOCUMENTACAO_DO_SISTEMA.md`, `backend/README.md`, `frontend/README.md` e arquivos de domínio). Nenhuma entrega de software é considerada completa com documentação divergente ou defasada.

Plataforma corporativa e determinística para acompanhamento, consolidação patrimonial, rentabilidade ponderada pelo tempo (TWR), Proventos, apuração fiscal de IRPF e simulação financeira de carteiras multiclasse.
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 Async (`asyncpg`), Alembic (head `20261105_purge_cert_entities`, 70 revisões), PostgreSQL 16, Redis 7 e APScheduler (12 jobs canônicos).
- **Frontend:** React 19 (`^19.3.1`), TypeScript 6 (`^6.0.3`), Vite 8 (`^8.3.4`), Tailwind CSS v4 (`^4.3.3`), TanStack Query v5, Zustand e Vitest.

## Ambientes de desenvolvimento e producao

Windows com Docker e o ambiente local de desenvolvimento e validacao na branch `stable-15jun`. OCI e producao na branch `main`.

Alteracoes chegam a `main` por Pull Request. Apos o merge e CI aprovado, GitHub Actions executa deploy automatico no SHA exato, salva backup pre-deploy e valida servicos, smoke, certificacao e `/ready`. Nao atualize a producao manualmente por SSH ou Compose. Consulte `docs/USER_VALIDATION_RUNBOOK.md` para validacao local e `docs/deployment/oci-execution-index.md` para o release.

## Suite de Ferramentas e Simuladores

A suite de ferramentas operacionais e de simulação reside sob `/carteira/ferramentas/*`:
- **Calculadora de Aportes/Rendimentos:** `/carteira/ferramentas/rendimentos` (juros compostos e aportes futuros);
- **Simulador de Renda Fixa:** `/carteira/ferramentas/renda-fixa` (dedução tributária regressiva ou isenção automática por taxonomia do produto);
- **Comparador de Ativos:** `/carteira/ferramentas/comparador` (análise comparativa simultânea de múltiplos e indicadores de até 5 ativos lado a lado);
- **Página de Análise de Ativos:** `/carteira/ferramentas/analise-ativos` (mergulho profundo por ticker com gráficos e múltiplos);
- **Carteiras Recomendadas por IA:** `/carteira/ferramentas/recomendacoes` (alocações institucionais de referência guiadas por IA para Patrimônio, Proventos e Performance, com simulação matemática por capital aportado).

Todas as ferramentas operam em memória e não modificam a custódia da carteira. Fórmulas, fontes e limites estão em [`docs/TOOLS_CALCULATORS.md`](docs/TOOLS_CALCULATORS.md).

No cadastro de Renda Fixa, o nome do título inclui o emissor, o tipo do produto define o tratamento fiscal e a carência é omitida sob liquidez diária. A taxonomia e as regras estão descritas em [`docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`](docs/FIXED_INCOME_TAXONOMY_INVENTORY.md).

## Branches e releases

- Windows/local: desenvolvimento e validacao em `stable-15jun`.
- OCI/producao: branch `main`.
- Alteracoes chegam a `main` por Pull Request; push direto e proibido.
- Apos merge e CI aprovado para o push em `main`, GitHub Actions executa deploy automatico no SHA exato, cria backup pre-deploy e valida saude, smoke, certificacao e `/ready`.
- `/ready` deve corresponder ao SHA, dataset e revisao Alembic ativos; `/health` isolado nao comprova certificacao.

Detalhes em `docs/deployment/oci-execution-index.md` e `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`.

## Funcionalidades e baseline de produção

A baseline confirmada em produção nesta revisão é a **PR #543** no SHA `93f7a2b2`. A branch local `stable-15jun` é a base de desenvolvimento e validação. A revisão canônica de banco está na migration `20261105_purge_cert_entities` (70 migrações lineares aplicadas). Consulte [`docs/ROADMAP.md`](docs/ROADMAP.md) para o histórico das entregas.

### Funcionalidades Implementadas e Ativas

- **Motor de Análise (#360) e Camada de IA (#361):** Análise determinística de diversificação patrimonial e concentração de ativos combinada com geração de resumos executivos e diagnósticos explicativos em linguagem natural (`frontend/src/pages/AnalisePage.tsx`).
- **Autenticação Google OAuth 2.0 & MFA TOTP (#97):** Login federado com Google e proteção com segundo fator (TOTP) integrados no fluxo de autenticação e no schema de banco.
- **Gaveta Consolidada de Detalhe de Ativo (#58 / #351):** `AssetDetailDrawer.tsx` com visualização detalhada em abas dinâmicas: visão geral, múltiplos fundamentalistas adaptados por classe (Ações, FIIs, BDRs, ETFs, Tesouro), histórico de cotações e proventos.
- **Suite Completa de Ferramentas (#359, #518, #521, #532):** Calculadora de aportes, Simulador de Renda Fixa, Comparador de Ativos, Análise Individual de Ativos e Carteiras Recomendadas por IA com simulador de alocação de capital.
- **Central de Ajuda e Assistente Documental com IA (#517, #526, #528):** `/carteira/ajuda` com busca rápida, atalhos dinâmicos de navegação no sistema e assistente em IA treinado exclusivamente no corpus funcional de `backend/help_docs/` com zero exposição de dados de custódia.
- **Evolução Patrimonial Contínua e Ponto em Tempo Real (#533):** Snapshots diários cobrindo fins de semana e feriados somados a ponto intradiário de alinhamento em tempo real no gráfico do Dashboard com cotações do pregão corrente.
- **Extrato Transacional com Alta Precisão e Usabilidade (#532, #543):** Modal de transações com máscara monetária decimal da direita para a esquerda (padrão Real BRL), suporte a operações a custo zero (R$ 0,00) para bonificações/doações, e filtro temporal dinâmico por período.
- **Unificação de Ações Fracionárias B3 (#524, #529):** Normalização contábil automática de ativos fracionários da B3 (descontinuação do sufixo `F` e unificação transparente no lote padrão `PETR4F` $\rightarrow$ `PETR4`).
- **Governança do Scheduler e Painel SuperAdmin (#501, #520):** Painel administrativo com monitoramento em tempo real de 12 tarefas agendadas, capacidade de disparo manual sob demanda e histórico detalhado de execuções com logs de duração e status.
- **Purga de Entidades Sintéticas (#525, #531):** Migrações para saneamento definitivo de contas e ativos sintéticos de certificação do banco de dados de produção.
- **Catálogo e Cotações Internacionais (`366ae927`):** Suporte nativo a Stocks e ETFs globais no bootstrap de dados e séries históricas consolidados via PTAX oficial.
- **Tabela Oficial de Proventos (`dea616ee`):** Detalhamento de proventos com tipo de provento, data-com, data de pagamento e valor unitário líquido, com notificação matinal automática por e-mail no dia do pagamento.
- **Taxonomia Canônica de Renda Fixa (#355):** Normalização fiscal automática derivada do tipo de produto, títulos com emissores integrados e liquidez diária.

### Mapeamento de Oportunidades de Melhoria

O diagnostico de 29/10/2026 e uma fotografia historica, nao um inventario confirmado do backlog atual. Consulte o relatorio [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md). O documento mapeia 19 oportunidades técnicas estruturadas por prioridade (P1 a P3), cobrindo integridade contábil, ampliação do `PortfolioAccessContext`, governança de branches e otimizações de performance.

## Agent Skills versionadas

Instruções operacionais para agentes vivem em `.agents/skills` e devem ser
atualizadas no mesmo bloco que alterar um contrato correspondente:

- `sgi-development` — branch, governança, Architecture Doctor e testes;
- `sgi-financial-data` — ledger, projeções e writes financeiros;
- `sgi-market-data` — providers, provenance, seeds e eventos corporativos;
- `sgi-certification` — identidade, `/ready`, promoção e revogação.

As skills orientam a leitura dos contratos vivos; não substituem Issues,
runbooks, testes ou autorização explícita para operações destrutivas/escritas.

## Ambientes

- Desenvolvimento: Windows, PowerShell e Docker, na branch `stable-15jun`.
- Producao: OCI, branch `main`, atualizacao automatica pelo GitHub Actions apos CI aprovado.

Deploy normal nao e feito manualmente por SSH. A identidade produtiva e a certificacao sao verificadas para o SHA exato do release; consulte o indice operacional OCI.

## Arquitetura financeira canônica

```text
bootstrap / sincronizadores explicitamente autorizados
        ↓
assets + asset_prices + rate_history + fx_rates
asset_dividends + corporate_events
        ↓
transactions
        ↓
projeções canônicas de posição, custo e resultado
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

Princípios obrigatórios:

- runtime financeiro DB-first;
- provider não participa de GET/cálculo financeiro;
- ausência não vira zero, câmbio fixo ou preço inventado;
- dados externos são persistidos antes de entrar em contratos financeiros;
- `transactions` é a fonte canônica do lifecycle, inclusive Renda Fixa e Tesouro;
- Proventos pertencem ao ativo em `asset_dividends`;
- o seed isolado de Proventos publica o contrato `pre-prod-dividends-seed.v2`; direitos de carteira são calculados sob demanda a partir das posições históricas, sem materialização por carteira;
- eventos corporativos pertencem ao ativo em `corporate_events`;
- rebuilds e seeds são operações explícitas e auditáveis.

## Estado funcional resumido

| Domínio | Estado em 01/11/2026 |
|---|---|
| Autenticação/Core | funcional com Google OAuth 2.0 e MFA TOTP (#97) |
| Carteiras/Transações | canônico e certificado sinteticamente |
| CSV | certificado |
| Patrimônio/Resumo | reconciliado em carteira assistida |
| Snapshots | rebuild/replay certificados com writer único canônico |
| Rentabilidade | TWR dedicado de Tesouro e Renda Fixa disponível; lacunas permanecem explícitas |
| Tesouro | valuation DB-first, snapshots dedicados e eventos monetários consumidos uma vez |
| Renda Fixa | lifecycle transaction-derived, taxonomia canônica unificada (#355) e TWR dedicado |
| Proventos | tabela oficial com tipo, data com/pag e valor unitário (`dea616ee`); `pre-prod-dividends-seed.v2` asset-based; direitos calculados sob demanda |
| Eventos corporativos | sem `UNRECONCILED` material; KLBN11 em `CONFLICT` revisável |
| IRPF | funcional para classes suportadas |
| Metas | superfície básica funcional; desenho definitivo permanece #246 |
| Detalhe de ativo | implementado via `AssetDetailDrawer.tsx` (#58 / #351) |
| Analysis Engine | implementado (#360) |
| IA de Análise | implementada com síntese executiva em linguagem natural (`AnalisePage.tsx`) (#361) |
| Central de Ajuda & IA Documental | implementada com RAG funcional local e atalhos (`HelpPage.tsx`) (#517, #526, #528) |
| Suite de Ferramentas | Calculadoras (#359), Comparador (#518), Análise de Ativos (#521) e Carteiras Recomendadas por IA (#532) |
| Livro-Razão & Transações | Extrato com filtro por período, máscara R$ decimal invertida e suporte a custo 0,00 (#532, #543) |
| Evolução Patrimonial | Snapshots diários incluindo fins de semana e ponto intradiário em tempo real (#533) |
| Normalização B3 | Fracionários unificados ao lote padrão no backend e na UI (#524, #529) |
| Painel Scheduler | Monitoramento de 12 jobs, trigger manual e histórico de execuções (#501, #520) |
| Ativos Internacionais | catálogo e séries históricas integrados (`366ae927`) |

## Registro historico de backlog

- **Entregas pós-GO consolidadas:** #58, #351, #355, #359, #360, #361 e #97 estão implementadas na baseline sincronizada `stable-15jun` / `main`.
- **Issues fechadas:** #352 (seletor de tipo de ativo), #354 (alinhamento de senha), #363, #364, #365.
- **Oportunidades Técnicas Priorizadas:** O planejamento registrado em 29/10/2026 e uma fotografia historica, nao uma lista confirmada de Issues abertas [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) (19 oportunidades mapeadas).
- **Pendências específicas:** #149 permanece aberta para evidência de posição de custódia por carteira na manhã do pagamento e base tributável/IRRF por lote do Tesouro Direto. #284 registra o historico da implantacao OCI; OCI atualmente e producao.

## Comandos básicos

```bash
cp .env.example .env
docker compose up -d --build
```

### Backend (Ambiente Local / `.venv`)

```powershell
cd backend
# Linting canônico (Flake8 com parâmetros oficiais de CI)
..\.venv\Scripts\python.exe -m flake8 app --max-line-length=120 --extend-ignore=E501,E221 --per-file-ignores="app/models/*.py:F821,F401" --jobs=1
# Verificação estrita de tipagem (Mypy)
..\.venv\Scripts\python.exe -m mypy app
# Validador de invariantes arquiteturais (Architecture Doctor)
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
# Validação de compilação
..\.venv\Scripts\python.exe -m compileall -q app tests
# Suíte de testes automatizados
..\.venv\Scripts\python.exe -m pytest tests/ -q
```

> **Nota sobre o Ruff:** O Ruff está instalado no ambiente e configurado como target opcional no `Makefile`, porém não possui `ruff.toml` dedicado no backend. O linter canônico do projeto é o **Flake8** com as diretivas acima.

### Frontend (Ambiente Local / Node.js 22+)

```powershell
cd frontend
npm run typecheck
npm run lint
npm test -- run
npm run build
```

### Gate assistido

```powershell
docker compose run --rm backend python -m app.cli.user_test_readiness
```

## Documentação canônica

- [`docs/DOCUMENTACAO_DO_SISTEMA.md`](docs/DOCUMENTACAO_DO_SISTEMA.md) — Manual unificado do sistema;
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Próximas atividades confirmadas e decisões vigentes;
- [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) — Diagnóstico histórico de 29/10/2026;
- [`backend/README.md`](backend/README.md) — Guia técnico e arquitetural do backend FastAPI;
- [`frontend/README.md`](frontend/README.md) — Guia técnico e arquitetural do frontend React 19;
- [`docs/architecture.md`](docs/architecture.md) — Arquitetura de domínios e contratos financeiros;
- [`ROADMAP.md`](ROADMAP.md) — Planejamento de entregas e reconciliação de marcos;
- [`CHANGELOG.md`](CHANGELOG.md) — Histórico de mudanças;
- [`docs/BOOTSTRAP_DATA_FLOW.md`](docs/BOOTSTRAP_DATA_FLOW.md) — Fluxo de inicialização e dados;
- [`docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`](docs/REAL_DATA_CERTIFICATION_RUNBOOK.md) — Certificação para dados reais;
- [`docs/DEVELOPMENT_BASELINE_2026-10-16.md`](docs/DEVELOPMENT_BASELINE_2026-10-16.md) — Registro histórico da baseline anterior.
