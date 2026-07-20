# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 20/07/2026

O SGI v2 opera com arquitetura **DB-first**: catálogo, preços, taxas, proventos e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

### Entregas consolidadas

- Valuation canônico por classe de ativo.
- Contratos `summary.v2` e `rentabilidade.v2` validados em runtime.
- Snapshots patrimoniais diários, mensais e por classe suportada.
- Histórico oficial da B3 via COTAHIST.
- Tesouro Direto com catálogo canônico, ano comercial de RendA+/Educa+ e preços oficiais persistidos.
- Renda Fixa valorizada por motor dedicado.
- CDI e IPCA servidos a partir de séries persistidas.
- Proventos monetários líquidos agregados por data de pagamento.
- Reconciliação entre Resumo, Patrimônio, Rentabilidade e snapshots.
- Cobertura parcial e retornos estimados explicitados no contrato.
- Página Resumo concluída, reconciliada com valuation e snapshots canônicos e promovida pela PR #164.
- Fase 2 de Proventos concluída sob a Issue #165 e promovida pela PR #166: pipeline DB-first, contratos estritos, filtros compartilhados, coleta global e materialização rastreável.
- Histórico mensal de proventos reconciliado por classe, com detalhamento acessível por mouse, teclado e toque.
- Fase 3 de Patrimônio concluída sob a Issue #148: históricos consolidados e por classe, períodos determinísticos, tooltips canônicos e reconciliações observáveis por base temporal.
- Valuation intradiário reconciliado entre `summary.v2`, posições e distribuição; snapshots consolidados reconciliados com classes somente na mesma data.
- Inventário pré-produção read-only validado no PostgreSQL real, com 24 tabelas, 4.671.361 registros, zero inconsistências canônicas e política completa de classificação no contrato `pre-prod-inventory.v2`.
- CLIs `pre_prod_backup` e `pre_prod_restore` implementados com dump custom, SHA-256, restauração transacional em banco vazio e isolado, novo inventário v2 e reconciliação integral; execução real da Issue #183 pendente.

### Tesouro Direto — Blocos 3.1 e 3.2

O fluxo usado pela página Resumo foi alinhado ao pipeline canônico:

- provedor primário de mercado para preços recentes;
- dados abertos oficiais do Tesouro como fallback;
- último preço persistido como contingência;
- resolução case-insensitive de tickers e aliases;
- preço devolvido pelo ticker original da posição;
- criação automática de ativos duplicados bloqueada;
- regressões para RendA+ adicionadas.

Os valores atuais de Selic e RendA+ foram validados na interface. A limpeza integral da base foi adiada para o checklist pré-produção e está registrada na issue #158.

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo canônico de ativos
        ↓
B3 COTAHIST | dados abertos oficiais do Tesouro | séries macroeconômicas | motores dedicados
        ↓
asset_prices / rate_history / proventos
        ↓
Valuation canônico por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 / rentabilidade.v2 / posições canônicas
        ↓
Resumo, Patrimônio, Rentabilidade e demais módulos
```

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, separação entre valuation intradiário e performance fechada e contratos financeiros únicos.

## Comandos operacionais

```bash
python -m app.cli.pre_prod_inventory
python -m app.cli.full_market_rebuild
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

## Prioridades atuais

1. Executar e validar backup/restauração isolada no PostgreSQL real (#183).
2. Somente após encerrar #183, preparar o dry-run de limpeza da #158.
3. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
4. Materializar o histórico persistido do IBOV (#150).
5. Remover o serviço legado de rentabilidade (#151).

## Dependências

A auditoria Dependabot da Issue #159 foi concluída. Atualizações compatíveis foram incorporadas à `stable-15jun` em blocos isolados. A incompatibilidade entre TypeScript 7 e `typescript-eslint@8.64.0` foi corrigida pela Issue #182, mantendo resolução estrita de peer dependencies.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only aprovado e sem tabelas desconhecidas;
2. backup validado com checksum e restauração isolada — CLIs implementados; execução real da #183 pendente;
3. exportação controlada das transações, renda fixa e eventos corporativos;
4. limpeza controlada de dados reconstruíveis;
5. seed B3 COTAHIST;
6. seed oficial do Tesouro Direto;
7. seed de benchmarks, câmbio e proventos;
8. importação CSV completa da carteira;
9. rebuild de posições e snapshots;
10. reconciliação financeira e auditoria de cobertura.

Checklist completo: issue #158. Runbook operacional: `docs/PRE_PROD_REBUILD_RUNBOOK.md`.

## Stack

Backend: Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e APScheduler.

Frontend: React 19, TypeScript, Vite, TailwindCSS 4, Recharts, React Query, Zustand e Axios.

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

## Documentação viva

- `ROADMAP.md` — prioridades e andamento modular.
- `ROADMAP_SPRINTS.md` — histórico de sprints.
- `CHANGELOG.md` — mudanças relevantes.
- `docs/architecture.md` — arquitetura DB-first.
- `docs/providers.md` — fontes e fallbacks.
- `docs/operations.md` — operação e rebuilds.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — política e sequência do rebuild pré-produção.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
- `docs/RESUMO_ARCHITECTURAL_AUDIT.md` — matriz de contratos e divergências da página Resumo.
- `docs/PROVENTOS_ARCHITECTURAL_AUDIT.md` — fluxo, contratos, riscos e sequência da Fase 2.
- `docs/PATRIMONIO_ARCHITECTURAL_AUDIT.md` — snapshots, históricos por classe e reconciliações da Fase 3.
