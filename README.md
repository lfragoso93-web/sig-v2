# SGI — Sistema de Gestão de Investimentos

> **Documentação Completa da Aplicação:** Consulte o manual técnico unificado em [`docs/DOCUMENTACAO_DO_SISTEMA.md`](docs/DOCUMENTACAO_DO_SISTEMA.md).
> **Relatório Oficial de Oportunidades de Melhoria:** [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md).
> **Guias Técnicos Dedicados:** Backend em [`backend/README.md`](backend/README.md) | Frontend em [`frontend/README.md`](frontend/README.md).

Plataforma corporativa e determinística para acompanhamento, consolidação patrimonial, rentabilidade ponderada pelo tempo (TWR), Proventos, apuração fiscal de IRPF e simulação financeira de carteiras multiclasse.
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 Async (`asyncpg`), Alembic (head `20261022_auth_oauth_mfa`), PostgreSQL 16, Redis 7 e APScheduler.
- **Frontend:** React 19 (`^19.3.1`), TypeScript 6 (`^6.0.3`), Vite 8 (`^8.3.4`), Tailwind CSS v4 (`^4.3.3`), TanStack Query v5, Zustand e Vitest.

## Ambiente de validação com usuários

O runtime único de desenvolvimento, testes e validação com usuários é o projeto Compose existente `docker-compose.yml` (`sig-v2`), publicado localmente ou via Cloudflare Tunnel. Toda alteração de produto validada com usuários deve ser incorporada às imagens backend/frontend dessa stack. Não iniciar `sgi-usertest`; o procedimento atual está em [`docs/USER_VALIDATION_RUNBOOK.md`](docs/USER_VALIDATION_RUNBOOK.md).

## Simulações e Calculadoras

A calculadora de aportes está em `/carteira/ferramentas/rendimentos`; o simulador de Renda Fixa está em `/carteira/ferramentas/renda-fixa`. No simulador, o tratamento de IR é derivado automaticamente da taxonomia do produto. Ambos usam premissas informadas pelo usuário, operam em memória e não modificam a carteira. Fórmulas, fontes e limites estão em [`docs/TOOLS_CALCULATORS.md`](docs/TOOLS_CALCULATORS.md).

No cadastro de Renda Fixa, o nome do título inclui o emissor, o tipo do produto define o tratamento fiscal e a carência é omitida sob liquidez diária. A taxonomia e as regras estão descritas em [`docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`](docs/FIXED_INCOME_TAXONOMY_INVENTORY.md).

## Branch e governança

- desenvolvimento obrigatório em `stable-15jun`;
- `main` recebe apenas macroblocos certificados via Pull Request;
- cada implementação é dividida em commits pequenos e rastreáveis;
- antes de alterar funcionalidade, revisar a Issue relacionada, contratos canônicos e impacto arquitetural;
- README, ROADMAP, CHANGELOG, Issues e runbooks devem refletir o estado real do projeto.

## Status do Projeto e Entregas Recentes — 29/10/2026

O SGI v2 opera sobre o branch obrigatório `stable-15jun`, com o banco de dados governado pelo Alembic na cabeça **`20261022_auth_oauth_mfa`** (67 revisões lineares encadeadas) e runtime unificado local no Docker Compose (`sig-v2`).

### Funcionalidades Implementadas e Ativas

- **Motor de Análise (#360) e Camada de IA (#361):** Análise determinística de diversificação patrimonial e concentração de ativos combinada com geração de resumos executivos e diagnósticos explicativos em linguagem natural (`frontend/src/pages/AnalisePage.tsx`).
- **Autenticação Google OAuth 2.0 & MFA TOTP (#97):** Login federado com Google e proteção com segundo fator (TOTP) integrados no fluxo de autenticação e no schema de banco.
- **Gaveta Consolidada de Detalhe de Ativo (#58 / #351):** `AssetDetailDrawer.tsx` com visualização detalhada em abas dinâmicas: visão geral, múltiplos fundamentalistas adaptados por classe (Ações, FIIs, BDRs, ETFs, Tesouro), histórico de cotações e proventos.
- **Simuladores Financeiros (#359):** Calculadora de aportes periódicos e simulador comparativo de Renda Fixa com dedução tributária automática conforme a taxonomia canônica (`/carteira/ferramentas/*`).
- **Catálogo e Cotações Internacionais (`366ae927`):** Suporte nativo a Stocks e ETFs globais no bootstrap de dados e séries históricas.
- **Tabela Oficial de Proventos (`dea616ee`):** Detalhamento de proventos com tipo de provento, data-com, data de pagamento e valor unitário líquido.
- **Taxonomia Canônica de Renda Fixa (#355):** Normalização fiscal automática derivada do tipo de produto, títulos com emissores integrados e liquidez diária.

### Mapeamento de Oportunidades de Melhoria

O diagnóstico técnico aprofundado do sistema encontra-se catalogado no relatório oficial [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md). O documento mapeia 19 oportunidades técnicas estruturadas por prioridade (P1 a P3), cobrindo integridade contábil, ampliação do `PortfolioAccessContext`, governança de branches e otimizações de performance.

## Agent Skills versionadas

Instruções operacionais para agentes vivem em `.agents/skills` e devem ser
atualizadas no mesmo bloco que alterar um contrato correspondente:

- `sgi-development` — branch, governança, Architecture Doctor e testes;
- `sgi-financial-data` — ledger, projeções e writes financeiros;
- `sgi-market-data` — providers, provenance, seeds e eventos corporativos;
- `sgi-certification` — identidade, `/ready`, promoção e revogação.

As skills orientam a leitura dos contratos vivos; não substituem Issues,
runbooks, testes ou autorização explícita para operações destrutivas/escritas.

## Ambiente de desenvolvimento e OCI

### Local

Windows + PowerShell + Docker é o ambiente oficial de desenvolvimento, correção, migrations de teste, suítes pesadas, certificação financeira e geração do SHA candidato.

### OCI

OCI não faz parte do caminho atual de desenvolvimento, testes ou homologação.
#284 preserva o trabalho de infraestrutura/cloud como backlog futuro.

Quando esse backlog for retomado, não desenvolver nem manter hotfix permanente
na VM.

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

| Domínio | Estado em 29/10/2026 |
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
| IA | implementada com síntese executiva em linguagem natural (`AnalisePage.tsx`) (#361) |
| Calculadoras & Simulação | implementadas em `/carteira/ferramentas/*` (#359) |
| Ativos Internacionais | catálogo e séries históricas integrados (`366ae927`) |

## Status do Backlog e Evolução

- **Entregas pós-GO consolidadas:** #58, #351, #355, #359, #360, #361 e #97 estão implementadas no branch `stable-15jun`.
- **Issues fechadas:** #352 (seletor de tipo de ativo), #354 (alinhamento de senha), #363, #364, #365.
- **Oportunidades Técnicas Priorizadas:** O planejamento das próximas rodadas de evolução técnica está formalizado no relatório oficial [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) (19 oportunidades mapeadas).
- **Pendências específicas:** #149 permanece aberta para evidência de posição de custódia por carteira na manhã do pagamento e base tributável/IRRF por lote do Tesouro Direto. #284 preserva o trabalho de infraestrutura em nuvem (OCI) como backlog futuro.

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
- [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) — Diagnóstico detalhado de melhorias e oportunidades;
- [`backend/README.md`](backend/README.md) — Guia técnico e arquitetural do backend FastAPI;
- [`frontend/README.md`](frontend/README.md) — Guia técnico e arquitetural do frontend React 19;
- [`docs/architecture.md`](docs/architecture.md) — Arquitetura de domínios e contratos financeiros;
- [`ROADMAP.md`](ROADMAP.md) — Planejamento de entregas e reconciliação de marcos;
- [`CHANGELOG.md`](CHANGELOG.md) — Histórico de mudanças;
- [`docs/BOOTSTRAP_DATA_FLOW.md`](docs/BOOTSTRAP_DATA_FLOW.md) — Fluxo de inicialização e dados;
- [`docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`](docs/REAL_DATA_CERTIFICATION_RUNBOOK.md) — Certificação para dados reais;
- [`docs/DEVELOPMENT_BASELINE_2026-10-16.md`](docs/DEVELOPMENT_BASELINE_2026-10-16.md) — Registro histórico da baseline anterior.
