# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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

- Tesouro Transparente adotado como fonte principal do catálogo e histórico.
- Brapi mantida como fallback secundário.
- Catálogo oficial sincronizado de forma idempotente.
- Aliases legados auditados e deduplicados.
- RendA+ convertido do vencimento final para o ano comercial.
- Educa+ convertido do vencimento final para o ano comercial.
- Histórico antigo migrado com proteção contra colisões de símbolos.
- Reconstrução limpa das séries oficiais.
- Validação concluída com todas as 46 transações de Tesouro reconhecidas.
- Snapshot validado com `treasury_matched=3` e `treasury_unresolved=0`.

#### B3 Historical Market Rebuild

- B3 COTAHIST adotado como fonte histórica primária para ações, FIIs, ETFs nacionais e BDRs.
- Arquivos anuais processados em lote, uma vez por ano consultado.
- Mercado à vista priorizado sobre mercado fracionário na mesma data.
- Persistência idempotente em `asset_prices`.
- Ativos deslistados preservados mesmo quando indisponíveis em provedores atuais.
- Ciclo de vida classificado como `COMPLETE`, `PRE_LISTING`, `DELISTED`, `REAL_GAP` ou `NO_HISTORY`.
- Primeira carga validada com 2.258 ativos e 984.949 preços entre 2024 e 2026.
- `PETZ3`, `SNAG11`, `AAZQ11`, `QQQI11` e `AREA11` deixaram de depender exclusivamente de provedores complementares.
- Período pré-negociação de `AREA11` passou a usar o custo da posição sem warning e sem estimativa indevida.

#### Operação e diagnóstico

- Novos comandos:
  - `python -m app.cli.sync_treasury_catalog_v2`;
  - `python -m app.cli.rebuild_treasury_official_prices`;
  - `python -m app.cli.rebuild_b3_historical_market`;
  - `python -m app.cli.repair_market_price_gaps`.
- Resumo de Proventos corrigido para resultados dataclass.
- Diagnósticos canônicos de Renda Fixa e Tesouro adicionados ao rebuild.
- Logs duplicados de cobertura removidos.
- Rebuilds de catálogo e histórico validados como idempotentes.

#### Validações reportadas

- Catálogo do Tesouro: 150 títulos oficiais, segunda execução sem alterações.
- Histórico do Tesouro: 88.181 preços oficiais reconstruídos.
- Auditoria do Tesouro: 46 transações válidas e nenhuma para revisão.
- B3 COTAHIST: 984.949 preços inseridos, 2.255 ativos completos, sem lacuna real detectada.
- Snapshots: 453 registros reconstruídos, sem erros.
- Renda Fixa validada com principal, valor corrigido e rendimento separados.

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

### Concluído — Consolidação financeira, CSV, Proventos e Tesouro Direto (10/07/2026)

- Serviço canônico de KPIs.
- Evolução patrimonial restaurada.
- Ganho realizado e retornos corrigidos.
- Seed histórico de proventos idempotente.
- Catálogo inicial de Tesouro consolidado.

## Próximos focos

- Auditar os cards da página Resumo contra os snapshots canônicos.
- Confirmar Resultado incluindo proventos materializados.
- Validar Rentabilidade desde o início dos lançamentos.
- Integrar operacionalmente o rebuild B3 ao fluxo completo.
- Ajustar a UI de Rentabilidade.
- Continuar eventos corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.
