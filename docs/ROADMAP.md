# Roadmap atual do SGI v2

> Revisado em 11/11/2026. Este é o índice vivo de próximas atividades. Inventários antigos permanecem em `history/` e não representam o estado atual das Issues, PRs ou do runtime.

## Ambientes e releases

- Desenvolvimento e validação local: Windows, branch `stable-15jun`.
- Produção: OCI, branch `main`.
- Alterações passam por validação local e Pull Request para `main`. O merge com CI aprovado dispara o deploy automático, com backup pré-deploy e verificação de identidade, smoke e `/ready`.
- O SHA implantado mais recentemente confirmado nesta revisão é `5c6e6949` (PR #571, sucedendo `b49fb7b2` / `5709af4d` das Fases 1–3). Cada novo SHA exige a certificação correspondente; `/ready` permanece fail-closed.
- A branch desta atividade parte de `stable-15jun` e incorpora `origin/main` antes da validação; os ponteiros remotos não são reescritos.

## Entregas concluídas

- **Snapshots por Classe em Transações de Fim de Semana, Tesouro UTC e Desambiguação de Classe em Valuation Canônico:** Correção de `rebuild_class_snapshots` em `portfolio_class_snapshot_service.py` para clonar transações de fim de semana com `fx_rate`/`price_brl` e carregar preços do Tesouro Direto por janela UTC (`start_ts..end_ts` sem deslocamento de fuso `func.date(timestamp)` em sessões `America/Sao_Paulo`), além de preservar `state.asset_type` em `portfolio_canonical_valuation_service.py` quando um ticker possui múltiplos registros em classes distintas.
- **Confiabilidade do Fechamento Diário, Câmbio (PTAX) e TWR Canônico:** Remoção do look-ahead de +1 dia em lifecycle_aware_price_service.py e silent_price_coverage_service.py com isolamento por (ticker, asset_type); criação do serviço e job recorrente sync_fx_rates_daily (x_rate_sync_service.py, PTAX oficial BCB em x_rates); fallbacks de fechamento para FII (Brapi stocks + Yahoo .SA) e CRIPTO (Yahoo USD/PTAX quando Brapi atrasa) em sset_price_gap_sync_service.py com ajuste BRT em sset_price_coverage_service.py; repescagens noturna/matinal (persist_daily_close_prices_catchup_night/morning e portfolio_snapshot_reconcile_late_data); e detecção automática de snapshots intradiários ou insumos mais novos (AssetPrice, FxRate, RateHistory) em portfolio_snapshot_twr_maintenance_service.py.
- **Bloqueio de Pesquisa e Cotação Estritamente por Classe:** Correção do alias `"STOCK"` em `asset_catalog_query_service.py`, filtro estrito por `asset_type` em `suggest_assets_from_catalog`, `search_assets`, `get_persisted_current_prices` e `_find_catalog_asset`, envio obrigatório de `asset_type` pelo `useTickerQuote` no `AddTransactionModal`, filtro opcional de classe em Análise e Comparação de Ativos, e trava de formato B3 em `verify_market_asset_exists` para impedir que ativos de uma classe respondam em outra.
- **Precedência Unificada de Chaves (`.env` → Painel Admin) e Filtro de Tickers Nacionais em Eventos Corporativos:** Resolução centralizada via `get_runtime_provider_key` (`BRAPI`, `ALPHA_VANTAGE`, `FINNHUB`, `TIINGO`) puxando o valor inicial do `.env` e aplicando imediatamente overrides salvos ou resetados no Painel Admin (`provider_configurations` + carga no startup da API); e filtro `_B3_ISSUER_TICKER_RE` para pular tickers nacionais fora do padrão B3 (como lançamentos manuais `BTC/ACAO`) sem gerar falsos alertas.
- **Resiliência de Conectores Estrangeiros, Scheduler de Eventos Corporativos e Cadência Intradiária:** Correção dos probes de conectividade em `provider_config_service.py` para injetar `X-Finnhub-Token` (`Finnhub`) e `Authorization: Token` (`Tiingo`), redução da frequência intradiária de ativos estrangeiros (`STOCK`/`ETF_INTERNACIONAL`) para 3 janelas/dia (11h, 14h e 17h BRT via `INTL_INTRADAY_HOURS`), TTL de banco estendido (`3600s`) e omissão de tickers estrangeiros não transacionados na varredura em lote de `quotes_service.py`; além de retry/backoff transitório em `B3ListedCompaniesClient._get_json` e isolamento por savepoint por ativo (`continue_on_asset_error=True`) no job diário `sync_corporate_events_daily`.
- **Fase 3 — Registro e Edição Manual de Liquidação de Frações Corporativas (`NIKE34`, `KLBN11`):** Persistência por carteira em `portfolio_corporate_fraction_settlements` (migration `20261111_fraction_settlements`) com rotas `PUT`/`DELETE /portfolios/{portfolio_id}/corporate-events/fraction-settlements` protegidas por `PortfolioAccessContext`, suporte no projetor canônico (`CASH_SETTLEMENT` com valor bruto informado e posições menores que 1 unidade), confirmação manual para direitos compostos (`KLBN11`) e painel interativo em `PendingCorporateFractionsPanel.tsx` com reconstrução automática de snapshots.
- **Fase 2 — Cobertura D-1 de Preços Persistidos, Expiração Diária de `HISTORY_END_UNAVAILABLE` e Desambiguação `(ticker, asset_type)`:** Correção do job diário `persist_daily_close_prices` (execução diária às 20h45 BRT com escopo Cripto aos fins de semana, `end_grace_days=0` e `include_start_gaps=False`), reabilitação automática de ativos marcados como `HISTORY_END_UNAVAILABLE` em dias anteriores (`provider_last_sync_at < required_to`), preservação de `HISTORY_START_EXHAUSTED` quando o provedor retorna apenas interseção inicial ou após `stale_end`, e filtragem estrita por `(ticker, asset_type)` em `persisted_price_query_service.py` para evitar colisões como `BTC (ACAO)` vs `BTC (CRIPTO)`.
- **Fase 1 — Classificação B3 (`AREA11`, `MELK3`), Avisos Não Bloqueantes de Custo Simbólico e Paridade SQLAlchemy:** Classificação exata de ações imobiliárias (`^[A-Z]{4}[345678]$`) e `AREA11` (`ETF_NACIONAL`) em `b3_investor_area_adapter_service.py`, retorno de `advisories` não bloqueantes no `CSVImportResponse` e `ImportCSVModal.tsx` quando eventos `"Atualização"` usam `R$ 0,01`, e teste flexível de paridade `2.1.x` em `test_sqlalchemy_21_runtime_contract.py`.
- **Atualização de Dependências e Segurança Estática (Dependabot PRs #534-#542, #560-#564 + CodeQL #233-#235):** Consolidação das atualizações compatíveis de backend (`fastapi >= 0.162.2`, `pypdf >= 7.0.0`, `sqlalchemy 2.1.8`, `pydantic 2.14.3`, `python-multipart 0.0.33`, `pytest-asyncio 1.4.1.post1`) e frontend (`axios ^1.21.0`, `@hookform/resolvers ^7.0.3`, `@tailwindcss/postcss ^4.3.5`, `@tanstack/react-query ^5.106.1`, `react-hook-form ^7.91.0`, `eslint ^10.14.0`, `jsdom ^31.0.0`, `vite ^8.3.6`, `@vitejs/plugin-react ^6.2.1`, `tailwindcss ^4.3.4`), retenção de TypeScript `^6.0.3` no `dependabot.yml` até suporte ao v7 pelo `typescript-eslint`, e eliminação de backtracking polinomial (ReDoS) nos adaptadores Sinacor e Tesouro (`brokerage_note_adapter_service.py` e `b3_investor_area_adapter_service.py`).
- **Release de Produção PR #558 / SHA `92a3c2f2`:** Deploy validado via GitHub Actions na infraestrutura OCI com certificação aprovada (precedido por PRs #543-#557).
- **Regra Obrigatória de Documentação Contínua e Viva:** Estabelecido o invariante de que qualquer instrução, refatoração, funcionalidade ou migração deve atualizar toda a documentação relevante (READMEs, ROADMAP, DOCUMENTACAO_DO_SISTEMA e manuais) no mesmo bloco de trabalho.
- **Suite Avançada de Ferramentas e IA (PRs #518, #521, #522, #523, #532):**
  - Comparador de Ativos com visualização simultânea de até 5 ativos lado a lado;
  - Página dedicada de Análise de Ativos com deep linking por ticker, gráficos de cotação e múltiplos;
  - Carteiras Recomendadas por IA com estratégias de Patrimônio, Proventos e Performance, acompanhadas de simulador matemático de aportes.
- **Central de Ajuda e Assistente Documental com IA (PRs #517, #526, #528):** Central de ajuda redesenhada, busca por tópicos, atalhos de navegação e assistente documental treinado exclusivamente no corpus de `backend/help_docs/` com zero exposição de dados de custódia.
- **Resiliência de Snapshots e Exclusão em Lote de Transações:**
  - Coordenador *single-flight* com coalescência pela menor data por carteira (`portfolio_snapshot_rebuild_queue`), eliminando contenção de locks e exaustão do pool em rajadas de mutações.
  - Exclusão em lote no backend (`POST /transactions/bulk-delete`) e UI (`Transacoes.tsx`) com seleção múltipla e limpeza por grupo filtrado.
- **Aprimoramento Contábil de Eventos Corporativos e Importações B3:**
  - Segregação de débitos de frações em grupamento (reverso) no adaptador B3, eliminando dupla dedução de quantidade.
  - Desambiguação de devoluções de aluguel de ações (BTC) vs compras a mercado com preservação de preço médio (PM).
  - Painel de Eventos Corporativos e Leilão de Frações no frontend com discriminação clara entre frações pendentes aguardando leilão e valores liquidados em conta.
- **Evolução Patrimonial Contínua e Ponto Intradiário (PR #533):** Snapshots diários consolidados aos finais de semana e feriados somados a ponto intradiário em tempo real no gráfico do Dashboard com cotações correntes.
- **Aprimoramento do Livro-Razão e Transações (PRs #532, #543):** Extrato com filtro por período, máscara decimal monetária da direita para a esquerda (padrão R$) e suporte formal a lançamentos com custo unitário R$ 0,00 (bonificações e doações).
- **Unificação de Ações Fracionárias B3 (PRs #524, #529):** Normalização contábil unificando códigos fracionários (sufixo `F`) ao lote padrão no backend, catalog e UI.
- **Governança do Scheduler e Painel SuperAdmin (PRs #501, #520):** Monitoramento dos 12 jobs em tempo real, capacidade de disparo manual sob demanda e histórico detalhado de execuções com logs.
- **Expansão Rigorosa do `PortfolioAccessContext` (PRs #503-#516):** Autorização por escopo de carteira aplicada a transações, IRPF, proventos, performance, metas e CLIs de certificação.
- **Purga de Entidades Sintéticas (PRs #525, #531):** Migrações Alembic `20261105_clean_cert_entities` e `20261105_purge_cert_entities` expurgando dados sintéticos de teste do banco de produção.
- **Branding Institucional SGI e Nova Landing Page (PRs #527, #530):** Alinhamento completo da marca SGI, eliminação de tokens legados e nova Landing Page responsiva.
- CI/CD de produção por merge em `main`, com backup antes do deploy e verificações pós-deploy.
- Sincronização recorrente de proventos (segunda a sábado, 08:00) e eventos corporativos (dias úteis, 22:00), além dos benchmarks pela manhã e à noite.
- Limite de reset de senha por usuário e desbloqueio auditado pelo SuperAdmin.

## Bloco concluído: automação confiável e documentação

- O painel SuperAdmin mostra a próxima execução e o resultado técnico mais recente dos jobs, com alerta visual para falha e indisponibilidade do Redis.
- Redis retém estado por até 90 dias; apenas o tipo da exceção é exposto. O texto da exceção não é persistido no status.
- Falhas são relançadas ao APScheduler após o registro e não aparecem como execução bem-sucedida.
- A auditoria mensal da fonte B3 permanece opt-in até confirmação da URL e do ano oficiais. O job é read-only; promoção do calendário segue uma etapa separada.
- O módulo legado não registrado de `rate_history` foi removido. A ingestão ativa usa o `benchmark_rate_service` pelo scheduler canônico.
- Este documento é a referência viva. Roadmaps e diagnósticos pontuais antigos estão identificados como históricos.

## Próximas atividades após este bloco

1. Atualizar a referência anual da fonte B3 quando a bolsa publicar novo calendário e, então, revisar a ativação da auditoria mensal.
2. Se o painel de jobs não for suficiente para a operação, escolher um canal e destinatários para alertas externos antes de implementar envio automático.
3. Retomar a revisão incremental de segurança e autorização pelo backlog vigente, evitando reabrir oportunidades já corrigidas nos relatórios de outubro.

## Decisões mantidas

- Não ativar transactional outbox sem um efeito externo ou não reconstruível que precise de entrega durável.
- Não aplicar automaticamente eventos `CONFLICT`, `UNRECONCILED` ou sem evidência suficiente ao ledger/projeções.
- Não confundir status técnico de execução de um job com cobertura, correção ou certificação dos dados obtidos.

## Fontes de verdade

- [`README.md`](../README.md): visão do produto e papéis dos ambientes.
- [`RELIABLE_ASYNC.md`](RELIABLE_ASYNC.md): locks e tarefas assíncronas.
- [`MARKET_CALENDAR_CONTRACT.md`](MARKET_CALENDAR_CONTRACT.md): auditoria e promoção do calendário B3.
- [`USER_VALIDATION_RUNBOOK.md`](USER_VALIDATION_RUNBOOK.md): validação local e PR.
- [`deployment/oci-execution-index.md`](deployment/oci-execution-index.md): release OCI.
- [`DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md): diagnóstico histórico, não inventário atual.
