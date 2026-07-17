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

### Sprint 5P — Auditoria funcional da página Resumo

- [x] KPIs confrontados com valuation e snapshots canônicos.
- [x] Proventos líquidos recebidos usados nos totais.
- [x] Contrato `summary.v2` estrito e versionado.
- [x] Cobertura de preços e referências temporais expostas.
- [x] Histórico mensal e período completo corrigidos.
- [x] Tabela de posições migrada para métricas canônicas.
- [x] Scheduler intradiário ajustado para 90 minutos.
- [ ] Bug visual do gráfico divergente registrado na issue #147.

### Sprint 5Q — Auditoria funcional da página Patrimônio

- [x] Cards alinhados à semântica do Resumo.
- [x] Evolução diária e mensal usando custo das posições abertas.
- [x] Fluxos externos segregados do resultado.
- [x] Período “Tudo” sem limite artificial.
- [x] Consolidação por classe consumindo endpoint canônico.
- [ ] Restaurar gráficos históricos por classe — issue #148.

### Sprint 5R — Infraestrutura TWR por classe

- [x] Modelo e migration de `PortfolioClassSnapshot`.
- [x] TWR diário e acumulado para classes com histórico suportado.
- [x] Backfill integrado ao endpoint de evolução.
- [x] Manutenção noturna consolidada e por classe.
- [x] Reconciliação com o snapshot consolidado.
- [x] Tratamento de fluxos em fins de semana.
- [x] Disponibilidade, materialização e qualidade expostas.
- [ ] TWR dedicado de Tesouro e Renda Fixa — issue #149.

### Sprint 5S — Auditoria funcional da página Rentabilidade

- [x] Contrato `rentabilidade.v2` estrito e versionado.
- [x] KPIs monetários derivados do `summary.v2`.
- [x] TWR mensal corrigido para composição dos retornos diários.
- [x] TWR por classe separado de resultado simples.
- [x] Tesouro e Renda Fixa com semântica explícita de valuation e resultado.
- [x] CDI e IPCA migrados para séries persistidas servidas pelo backend.
- [x] Resultado por ativo migrado para posições e PnL realizado canônicos.
- [x] Reconciliação final entre Rentabilidade, Resumo, Patrimônio e classes.
- [x] Ausência de snapshots representada por `null`, sem falso zero.
- [ ] Histórico persistido do IBOV — issue #150.
- [ ] Remoção definitiva do serviço legado — issue #151.

## Em desenvolvimento

### Proventos

- [x] Materialização por carteira.
- [x] Totais canônicos líquidos recebidos.
- [ ] Validar cobertura completa por classe.
- [ ] Melhorar diagnóstico de eventos não materializados.

### Eventos corporativos — #129

- [x] Fundação de aliases e mudança de ticker.
- [ ] Splits, grupamentos e bonificações.
- [ ] Simulação, confirmação e rollback.
- [ ] Administração e auditoria.

## Próximas entregas prioritárias

1. Restaurar os gráficos por classe da página Patrimônio (#148).
2. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
3. Materializar histórico persistido do IBOV (#150).
4. Remover o serviço legado de rentabilidade (#151).
5. Corrigir o gráfico divergente da página Resumo (#147).
6. Concluir validação funcional do módulo Proventos.

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
3. Validação local, GitHub Actions e Render.
4. Atualização de README, roadmap e changelog ao consolidar uma entrega.
5. PR única para `main` ao concluir um bloco estável.
