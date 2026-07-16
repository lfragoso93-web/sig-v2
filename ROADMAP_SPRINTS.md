# Roadmap de Sprints — SGI v2

> Última atualização: 16/07/2026

Este documento preserva o histórico de sprints. O acompanhamento modular atual está em [`ROADMAP.md`](./ROADMAP.md).

## Sprints concluídas

### Sprint 1 — Fundação

- FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e Docker Compose.
- Autenticação JWT, usuários, carteiras, transações e posições.

### Sprint 2 — Core Financeiro

- Proventos, performance, câmbio, Tesouro Direto e ativos internacionais.
- Cache, scheduler e rate limiting.

### Sprint 3 — Funcionalidades avançadas base

- Metas, IRPF base, análise base, Renda Fixa, preços e alocação por classe.

### Sprint 4 — Catálogo e dados

- Seed idempotente de ativos.
- Backfill de preços.
- Onboarding e jobs incrementais.

### Sprint 5 — Dashboard e experiência principal

- Resumo, Patrimônio, Rentabilidade, Proventos e interface responsiva.
- Gráficos, benchmarks, distribuição por classe e metas.

### Sprint 5J — Estabilização funcional e contratos operacionais

- [x] KPIs canônicos para Resumo, Patrimônio e Rentabilidade.
- [x] Variação diária separada da rentabilidade acumulada.
- [x] Importação CSV com preview e `dry_run`.
- [x] Administração de usuários e integridade de carteiras.
- [x] Compliance público e documentação.

### Sprint 5K — Integridade histórica e modernização de dados

- [x] Cliente v2 e resolução de tickers antigos.
- [x] Aliases históricos.
- [x] Validação temporal de renomes no CSV.
- [x] Rebuild automático de snapshots após importações.
- [x] Fundação do evento `TICKER_CHANGE`.

### Sprint 5L — Arquitetura DB-first e TWR

- [x] Remover consultas externas do motor de snapshots.
- [x] Auditoria de cobertura por ativo.
- [x] Gap sync idempotente.
- [x] Metadados persistentes de provedor.
- [x] `full_market_rebuild` como comando operacional oficial.
- [x] TWR diário, mensal, 12 meses e desde o início.
- [x] Proventos em lotes seguros.
- [x] Sanitização de preços inválidos.

### Sprint 5M — Valuation canônico por classe

- [x] Renda Fixa valorizada pelo motor dedicado.
- [x] Tesouro valorizado pelo histórico oficial persistido.
- [x] Diagnósticos de principal, valor corrigido e rendimento.
- [x] Diagnósticos de títulos resolvidos e não resolvidos.
- [x] Exclusão de Tesouro e Renda Fixa do lookup genérico.
- [x] `return_is_estimated` derivado da cobertura real.

### Sprint 5N — Treasury Catalog v2

- [x] Fonte oficial do Tesouro como origem principal.
- [x] Provedor complementar como fallback.
- [x] Catálogo oficial idempotente.
- [x] Deduplicação de aliases legados.
- [x] RendA+ e Educa+ normalizados pelo ano comercial.
- [x] Migração segura dos históricos antigos.
- [x] Reconstrução limpa do histórico oficial.
- [x] Validação final com `treasury_matched=3` e `treasury_unresolved=0`.

### Sprint 5O — B3 Historical Market Rebuild

- [x] B3 COTAHIST como fonte histórica primária para ativos brasileiros.
- [x] Leitura anual em lote.
- [x] Mercado à vista priorizado sobre fracionário.
- [x] Persistência idempotente em `asset_prices`.
- [x] Atualização de `last_price`.
- [x] Ciclo de vida `COMPLETE`, `PRE_LISTING`, `DELISTED`, `REAL_GAP` e `NO_HISTORY`.
- [x] Validação com 2.258 ativos e 984.949 preços de 2024 a 2026.
- [x] Preservação de PETZ3 e outros ativos indisponíveis em provedores atuais.
- [x] Pré-listagem de AREA11 tratada sem falso erro de cobertura.

## Em desenvolvimento

### Resumo

- [ ] Auditar cards contra snapshots canônicos.
- [ ] Confirmar Resultado incluindo proventos totais.
- [ ] Validar Rentabilidade desde o início.
- [ ] Comparar Resumo e Patrimônio.
- [ ] Cobrir contratos dos cards com testes.

### Rentabilidade

- [x] Backend TWR consolidado.
- [x] Indicadores de qualidade calculados.
- [ ] Ajustar apresentação visual.

### Proventos

- [x] Materialização por carteira.
- [ ] Validar cobertura completa por classe.
- [ ] Confirmar impacto final nos KPIs durante a auditoria do Resumo.

### Eventos corporativos — #129

- [x] Fundação de aliases e mudança de ticker.
- [ ] Splits, grupamentos e bonificações.
- [ ] Simulação, confirmação e rollback.
- [ ] Administração e auditoria.

## Próximas entregas prioritárias

1. Auditoria dos cards da página Resumo.
2. Validação de Resultado + proventos + TWR desde o início.
3. Integração operacional do COTAHIST ao rebuild completo.
4. Ajustes visuais de Rentabilidade.
5. Próximos blocos de eventos corporativos.

## Backlog planejado

- Backup/Restore — #83.
- Google OAuth — #97.
- IRPF — #56.
- Análise de Carteira — #57.
- Janela Global do Ativo — #58.
- Provedores configuráveis — #127.

## Processo de desenvolvimento

1. Desenvolvimento sempre na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação local de build, testes e fluxo funcional.
4. Atualização de README, roadmap e changelog ao consolidar uma entrega.
5. PR única para `main` ao concluir um bloco estável.