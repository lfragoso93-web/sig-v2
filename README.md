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
- Fase 2 de Proventos concluída sob a Issue #165 e promovida pela PR #166.
- Fase 3 de Patrimônio concluída sob a Issue #148.
- Auditoria Dependabot concluída e Issue #159 encerrada.
- Inventário read-only pré-produção disponível pelo contrato `pre-prod-inventory.v1`.

### Tesouro Direto — Blocos 3.1 e 3.2

O fluxo usado pela página Resumo foi alinhado ao pipeline canônico:

- provedor primário de mercado para preços recentes;
- dados abertos oficiais do Tesouro como fallback;
- último preço persistido como contingência;
- resolução case-insensitive de tickers e aliases;
- preço devolvido pelo ticker original da posição;
- criação automática de ativos duplicados bloqueada;
- regressões para RendA+ adicionadas.

Os valores atuais de Selic e RendA+ foram validados na interface. A limpeza integral da base está registrada na Issue #158.

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

1. Validar o inventário pré-produção em banco real e anexar o relatório à Issue #176.
2. Preparar backup e teste de restauração da Issue #158.
3. Rentabilidade: implementar TWR dedicado para Tesouro e Renda Fixa (#149).
4. Materializar o histórico persistido do IBOV (#150).
5. Remover o serviço legado de rentabilidade (#151).

## Dependências

A auditoria do Dependabot foi concluída na Issue #159. As atualizações compatíveis foram integradas à `stable-15jun`; TypeScript 7 foi revertido para a linha 6.0.3 após incompatibilidade confirmada com `typescript-eslint@8.64.0` na Issue #182.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only e relatório de impacto;
2. backup validado e teste de restauração;
3. limpeza controlada de dados reconstruíveis;
4. seed B3 COTAHIST;
5. seed oficial do Tesouro Direto;
6. seed de benchmarks e proventos;
7. importação CSV completa da carteira;
8. rebuild de posições e snapshots;
9. reconciliação financeira e auditoria de cobertura.

Checklist completo: Issue #158. Runbook operacional: `docs/PRE_PROD_REBUILD_RUNBOOK.md`.

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
- `docs/operations.md` — operação, inventário e rebuilds.
- `docs/PRE_PROD_REBUILD_RUNBOOK.md` — segurança e sequência do rebuild pré-produção.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
- `docs/RESUMO_ARCHITECTURAL_AUDIT.md` — matriz de contratos e divergências da página Resumo.
- `docs/PROVENTOS_ARCHITECTURAL_AUDIT.md` — fluxo, contratos, riscos e sequência da Fase 2.
- `docs/PATRIMONIO_ARCHITECTURAL_AUDIT.md` — snapshots, históricos por classe e reconciliações da Fase 3.
