# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Adicionado — Auditoria funcional canônica de Resumo, Patrimônio e Rentabilidade (16/07/2026)

#### Contratos financeiros

- Novo contrato financeiro oficial em `docs/CANONICAL_FINANCIAL_CONTRACT.md`.
- Contrato `summary.v2` versionado, estrito e validado em runtime.
- Contrato `rentabilidade.v2` versionado, estrito e validado em runtime.
- Campos legados e aliases financeiros removidos dos contratos ativos.
- Respostas antigas de cache passam a ser rejeitadas e recalculadas.
- Ausência de TWR passou a ser representada por `null`, e não por falso `0%`.
- Metadados de fonte, cobertura, estimativa e referência temporal adicionados.

#### Página Resumo

- KPIs reconciliados com valuation intradiário, snapshots fechados e proventos canônicos.
- Patrimônio intradiário separado de TWR fechado.
- Resultado total separado em realizado, não realizado e proventos.
- Proventos por ticker e classe limitados a eventos monetários líquidos recebidos.
- Histórico mensal baseado no último snapshot de cada mês.
- “Todo período” corrigido para não limitar a série a 60 meses.
- Tabela de posições migrada para contrato canônico.
- Variação diária separada de resultado patrimonial acumulado.
- Cobertura de preços e reconciliação expostas no payload.
- Bug visual do gráfico divergente registrado na issue #147.

#### Página Patrimônio

- Cards alinhados ao mesmo contrato financeiro da página Resumo.
- Evolução diária e mensal passou a usar `cost_basis` das posições abertas.
- `invested_total` preservado apenas como fluxo externo acumulado.
- Aportes e retiradas expostos separadamente no tooltip.
- Período “Tudo” corrigido para histórico completo.
- Distribuição por classe passou a consumir endpoint canônico.
- Regressão dos gráficos históricos por classe registrada na issue #148.

#### TWR por classe

- Novo modelo `PortfolioClassSnapshot`.
- Migration `20260716_class_snapshots` adicionada.
- TWR diário e acumulado por classe para ações, FIIs, ETFs, BDRs, stocks e cripto.
- Fluxos de compra, venda e proventos segregados por classe.
- Operações e pagamentos de fins de semana transportados para o próximo fechamento útil.
- Backfill por classe integrado ao endpoint de evolução.
- Manutenção noturna consolidada e por classe.
- Disponibilidade, materialização, cobertura e estado estimado expostos.
- Reconciliação com o snapshot consolidado adicionada.
- TWR dedicado de Tesouro e Renda Fixa registrado na issue #149.

#### Página Rentabilidade

- KPIs monetários derivados do `summary.v2`.
- TWR diário, mensal, 12 meses e desde o início derivado dos snapshots.
- Gráfico mensal corrigido para usar `monthly_return_pct` composto.
- TWR por classe separado de resultado patrimonial simples.
- Tesouro Direto identificado como marcação a mercado, sem falso TWR.
- Renda Fixa identificada como accrual por indexador, sem falso TWR.
- CDI composto a partir das taxas diárias persistidas.
- IPCA lido da série mensal persistida.
- Consultas diretas do frontend a BCB e provedores de índice removidas.
- Resultado por ativo migrado para posições canônicas e PnL realizado por ticker.
- Endpoint de reconciliação da página adicionado com tolerância de R$ 0,01.
- Histórico persistido do IBOV registrado na issue #150.
- Remoção do serviço legado de rentabilidade registrada na issue #151.

#### Scheduler e operação

- Atualização intradiária de preços alterada de 15 para 90 minutos em dias úteis.
- Invalidação de caches associada à atualização de cotações.
- Manutenção de snapshots por classe integrada ao job noturno.
- Revision Alembic encurtada para compatibilidade com `VARCHAR(32)`.
- Import histórico de câmbio corrigido para usar o serviço existente.
- Deploy e migration validados no Render.

#### Testes e diagnóstico

- Testes de contratos `summary.v2` e `rentabilidade.v2`.
- Testes de agregação canônica de proventos.
- Testes de snapshots e TWR por classe.
- Testes de reconciliação monetária.
- Testes de períodos completos e transformação dos gráficos.
- Testes de cadência do scheduler.
- Teste que impede revisions Alembic acima de 32 caracteres.

### Adicionado — Fontes oficiais, valuation canônico e qualidade dos snapshots (16/07/2026)

#### Valuation e snapshots

- Valuation canônico separado por classe de ativo.
- Renda Fixa passou a usar contratos, resgates e indexadores próprios.
- Tesouro Direto passou a usar o histórico oficial persistido.
- Tesouro e Renda Fixa foram removidos do lookup genérico de preços.
- Snapshots TWR reconstruídos com dados exclusivamente persistidos.
- `has_partial_prices` e `return_is_estimated` passaram a refletir cobertura real.
- Pré-listagem deixou de ser tratada como lacuna de preço.
- Resultado financeiro permanece separado da rentabilidade percentual.
- Resultado considera ganho realizado, ganho não realizado e proventos.

#### Treasury Catalog v2

- Fonte oficial do Tesouro adotada como origem principal do catálogo e histórico.
- Provedor complementar mantido como fallback secundário.
- Catálogo oficial sincronizado de forma idempotente.
- Aliases legados auditados e deduplicados.
- RendA+ e Educa+ convertidos para o ano comercial.
- Histórico antigo migrado com proteção contra colisões de símbolos.
- Reconstrução limpa das séries oficiais.
- Validação concluída com todas as 46 transações de Tesouro reconhecidas.
- Snapshot validado com `treasury_matched=3` e `treasury_unresolved=0`.

#### B3 Historical Market Rebuild

- B3 COTAHIST adotado como fonte histórica primária para ações, FIIs, ETFs nacionais e BDRs.
- Arquivos anuais processados em lote.
- Mercado à vista priorizado sobre mercado fracionário na mesma data.
- Persistência idempotente em `asset_prices`.
- Ativos deslistados preservados.
- Ciclo de vida classificado como `COMPLETE`, `PRE_LISTING`, `DELISTED`, `REAL_GAP` ou `NO_HISTORY`.
- Primeira carga validada com 2.258 ativos e 984.949 preços entre 2024 e 2026.

#### Operação e diagnóstico

- Novos comandos:
  - `python -m app.cli.sync_treasury_catalog_v2`;
  - `python -m app.cli.rebuild_treasury_official_prices`;
  - `python -m app.cli.rebuild_b3_historical_market`;
  - `python -m app.cli.repair_market_price_gaps`.
- Diagnósticos canônicos de Renda Fixa e Tesouro adicionados ao rebuild.
- Rebuilds de catálogo e histórico validados como idempotentes.

### Adicionado — Arquitetura DB-first, histórico canônico e TWR (14/07/2026)

- Novo orquestrador `full_market_rebuild`.
- Auditoria de cobertura histórica por ativo.
- Gap sync idempotente com locks e concorrência controlada.
- Metadados persistentes de provedor.
- Smart sync com `HISTORY_START_EXHAUSTED`.
- Sanitização de preços anômalos.
- Materialização de proventos em lotes seguros.
- Endpoints de evolução diária e mensal migrados para snapshots enriquecidos.
- KPIs de Rentabilidade com retorno diário, mensal, 12 meses e desde o início.

### Adicionado — Integração v2, aliases e eventos corporativos (13/07/2026)

- Cliente isolado para API v2.
- Resolução em lote de tickers antigos.
- Modelo de aliases históricos.
- Evento `TICKER_CHANGE` idempotente.
- Conversão automática de saldo remanescente.
- Reconstrução automática de snapshots após importação CSV.
- Filtros interativos no modal CSV.
- Edição de nome e descrição de carteiras.

### Concluído — Compliance público e hardening documental (11/07/2026) — #80

- Documentação pública sanitizada.
- OpenAPI e respostas públicas sem identificação desnecessária de fornecedores.
- Variáveis genéricas de configuração adicionadas com compatibilidade legada.

### Concluído — Resumo, administração e integridade operacional (11/07/2026)

- Variação diária separada da rentabilidade acumulada.
- Dropdowns renderizados via portal.
- Exclusão segura de carteiras.
- Administração de usuários e proteção do último superadmin.
- Importação CSV com bloqueios e invalidação de caches.

## Próximos focos

- Restaurar gráficos históricos por classe na página Patrimônio (#148).
- Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
- Materializar histórico persistido do IBOV (#150).
- Remover serviço legado de rentabilidade (#151).
- Corrigir gráfico divergente da página Resumo (#147).
- Concluir validação funcional de Proventos.
- Continuar eventos corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.
