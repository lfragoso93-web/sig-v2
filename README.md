# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 22/07/2026

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
- Inventário pré-produção read-only validado no PostgreSQL real, com 24 tabelas, política completa de classificação e contrato `pre-prod-inventory.v2`.
- Backup `pre-prod-backup.v3` validado no PostgreSQL real com cliente/servidor 16/16, snapshot único `REPEATABLE READ READ ONLY`, dump com SHA-256, restauração em banco vazio e isolado e reconciliação `ok=true`, sem divergências e com zero escritas na origem. A Issue #183 foi concluída e a PR #184 promovida para a `main`.
- Dry-run de limpeza validado no PostgreSQL real pelo contrato `pre-prod-cleanup-impact.v2`: 24 tabelas, 4.673.320 linhas, 11 preservadas, 3 com exportação obrigatória, 10 reconstruíveis, zero bloqueios, zero ciclos e zero escritas. A execução `20260722-101848` retornou `ok=true` e exit code `0`.
- Exportação auditável `pre-prod-export.v1` validada no PostgreSQL real em snapshot único `REPEATABLE READ READ ONLY`: `corporate_events`, `fixed_income_investments` e `transactions` reconciliadas em 323 linhas, com SHA-256 de dados e schema, zero escritas na origem e `reconciled=true`. A execução `20260722-134741` retornou exit code `0`, a Issue #188 foi encerrada e a PR #191 promovida para a `main`.
- Migração integral das configurações Pydantic v2 para `ConfigDict` concluída na Issue #186. A suíte dedicada passou com 5 testes e a validação final registrou `666 passed`, `1 skipped` intencional e zero `PydanticDeprecatedSince20`.

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
python -m app.cli.pre_prod_backup
python -m app.cli.pre_prod_restore
python -m app.cli.pre_prod_cleanup_impact
python -m app.cli.pre_prod_export
python -m app.cli.full_market_rebuild
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

## Prioridades atuais

1. Implementar o contrato e o serviço de limpeza controlada das tabelas reconstruíveis da #158, usando o gate aprovado e os artefatos exportados da Issue #188, sem executar escrita real no primeiro sub-bloco.
2. Executar a limpeza e o rebuild pré-produção em etapas auditáveis.
3. Remover o serviço legado de rentabilidade (#151).
4. Materializar o histórico persistido do IBOV (#150).
5. Implementar TWR dedicado, separando Tesouro Direto e Renda Fixa (#149).
6. Migrar timestamps UTC legados para timezone-aware (#192).

## Dependências

A auditoria Dependabot da Issue #159 foi concluída. Atualizações compatíveis foram incorporadas à `stable-15jun` em blocos isolados. A incompatibilidade entre TypeScript 7 e `typescript-eslint@8.64.0` foi corrigida pela Issue #182, mantendo resolução estrita de peer dependencies. Não há PR Dependabot aberta após o merge da PR #191.

## Pré-produção

A primeira entrada em produção exige:

1. inventário read-only aprovado e sem tabelas desconhecidas — concluído;
2. backup validado com checksum e restauração isolada — concluído pela Issue #183;
3. dry-run read-only da limpeza e relatório de impacto — validado pela Issue #185;
4. exportação controlada das transações, renda fixa e eventos corporativos — validada pela Issue #188 e promovida pela PR #191;
5. limpeza controlada de dados reconstruíveis;
6. seed B3 COTAHIST;
7. seed oficial do Tesouro Direto;
8. seed de benchmarks, câmbio e proventos;
9. importação CSV completa da carteira;
10. rebuild de posições e snapshots;
11. reconciliação financeira e auditoria de cobertura.

Checklist completo: issue #158. Runbook geral: `docs/PRE_PROD_REBUILD_RUNBOOK.md`. Runbook do dry-run: `docs/pre-prod-cleanup-impact-runbook.md`. Runbook da exportação: `docs/pre-prod-export-runbook.md`.

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
- `docs/pre-prod-cleanup-impact-runbook.md` — execução, artefato, exit codes e critérios de aborto do dry-run.
- `docs/pre-prod-export-runbook.md` — execução read-only, artefatos, manifesto, reconciliação e códigos de saída da exportação.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
- `docs/RESUMO_ARCHITECTURAL_AUDIT.md` — matriz de contratos e divergências da página Resumo.
- `docs/PROVENTOS_ARCHITECTURAL_AUDIT.md` — fluxo, contratos, riscos e sequência da Fase 2.
- `docs/PATRIMONIO_ARCHITECTURAL_AUDIT.md` — snapshots, históricos por classe e reconciliações da Fase 3.