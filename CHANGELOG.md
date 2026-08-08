# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Alterado — bootstrap v3, FX certificado e Proventos gated (08/08/2026)

- O checkpoint `0e8d96c081a0e788a9edcf69901a134b29b7f696` foi certificado localmente pelo usuário com build Docker aprovado, 22/22 testes dirigidos, `compileall` e import integral de `app.main` aprovados.
- O bootstrap passou a exigir identidade auditável compartilhada (`run_id`, branch `stable-15jun` e SHA completo); o disparo administrativo exige o SHA e o startup pode recebê-lo por `SGI_BOOTSTRAP_COMMIT_SHA`.
- O contrato `system-bootstrap.v2` incorporou câmbio USD-BRL reutilizando o seed transacional PTAX já certificado pela #217, com cobertura própria desde `1994-07-01` e sem fallback BRAPI/AwesomeAPI/fixo.
- A cobertura temporal deixou de ser um parâmetro global: cada domínio define sua maior janela válida conforme a fonte canônica.
- O contrato evoluiu para `system-bootstrap.v3` com etapa explícita `asset_dividends`, reutilizando `pre-prod-dividends-seed.v2` e os adapters estritos BRAPI/Yahoo já existentes.
- Proventos permanecem fail-closed: sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, a etapa aborta antes de consultar providers; esse opt-in técnico não substitui a autorização operacional exigida pela #226.
- O estágio de Proventos escreve exclusivamente em `asset_dividends`, não utiliza `dividend_backfill_service` e não materializa direitos por carteira.
- `ready_for_real_data` permanece `false`; eventos corporativos são o próximo domínio obrigatório do bootstrap antes da certificação final.
- README, ROADMAP, arquitetura, continuidade e Issues #248/#250/#226 foram sincronizados com o novo estado.

### Alterado — readiness, lacuna pontual e catálogo DB-first (07/08/2026)

- O checkpoint `113281b7a0153f02007d6d49761be8fef91d77a8` foi certificado localmente com 26/26 testes, `compileall` e import integral de `app.main` aprovados.
- A Issue #249 foi concluída: `/health` representa liveness/dependências e `/ready` representa readiness operacional, mantendo `ready_for_real_data=false` enquanto o bootstrap global da #248 não estiver completo e certificado.
- Criado `price_date_gap_resolver_service.py` como única exceção dedicada para cotação histórica ausente: leitura DB-first inicial, janela externa limitada a `target_date - 5 dias .. target_date`, persistência em `asset_prices` e nova leitura DB-first.
- `get_price_at_date()` permanece leitor puro e não importa o resolvedor; o fallback pontual não usa `period=max`, backfill global ou `stale_snapshot`.
- Criado `asset_catalog_query_service.py` para sugestões e busca de Tesouro exclusivamente sobre o catálogo persistido pelo bootstrap.
- `assets.py` deixou de importar providers diretamente para catálogo e histórico: `/suggest` e `/tesouro/search` são DB-first; histórico em `/quote/{ticker}` e `/tesouro/price` usa o resolvedor pontual; apenas cotação atual/intraday continua passando pela fachada canônica de preços.
- Ativos desconhecidos não são mais descobertos implicitamente por provider durante requests; precisam existir no catálogo persistido.
- Novos gates estruturais protegem a fronteira de provider do router e do catálogo.

### Alterado — orquestrador global de bootstrap (07/08/2026)

- Criado `system_bootstrap_service.py` como porta única para o bootstrap inicial do ambiente.
- O contrato `system-bootstrap.v1` produz relatório estruturado por etapa e interrompe a cadeia após falha, evitando que estágios dependentes avancem silenciosamente.
- A sequência procedural `_boot_sequence()` foi removida de `app.main`; o lifespan agora apenas delega ao orquestrador global quando `ENABLE_BOOT_MARKET_SYNC` está habilitado.
- O primeiro bloco migra somente etapas já existentes e previamente autorizadas: catálogo de ativos, catálogo/reconciliação/histórico de Tesouro, histórico global de preços e benchmarks.
- Proventos, eventos corporativos e câmbio permanecem explicitamente fora do `system-bootstrap.v1` até seus gates serem incorporados pela #248; um relatório verde deste primeiro contrato ainda não libera dados reais.
- Adicionados gates estruturais para impedir reintrodução de lógica de seed/backfill diretamente em `app.main` e inclusão silenciosa de domínios bloqueados no bootstrap.

### Alterado — política canônica de bootstrap e providers (07/08/2026)

- Definido que o ambiente deve executar um bootstrap inicial idempotente e certificável antes de liberar criação/importação de carteiras reais.
- O bootstrap deve persistir catálogo/metadados de ativos, históricos, Proventos, eventos corporativos, Tesouro, benchmarks, câmbio e demais séries necessárias ao funcionamento do SGI v2.
- Depois do bootstrap, requests funcionais e cálculos financeiros passam a ser estritamente DB-first.
- Consultas externas recorrentes em runtime ficam limitadas a preço intraday e preço oficial/de fechamento diário; esses preços devem ser persistidos antes de alimentar contratos financeiros.
- Busca de ativos, detalhes, posições, relatórios, Proventos, IRPF e rentabilidade não devem consultar providers diretamente.
- README, ROADMAP, arquitetura e continuidade foram sincronizados com essa fronteira.
- O desenho atual de `assets`, scheduler e entrypoint deve ser reavaliado na #247 para eliminar chamadas externas que não pertençam à nova regra.

### Corrigido — superfícies financeiras read-only e rebuild explícito (07/08/2026)

- Removida a porta HTTP pública `POST /api/v1/performance/{portfolio_id}/evolution/backfill`; os serviços internos de reconstrução permanecem disponíveis apenas para fluxos operacionais explícitos.
- O router de `performance` ficou exclusivamente read-only e recebeu gate contra reintrodução de POST/backfill/rebuilders.
- Os GETs de `positions` deixaram de aceitar `refresh=true` e não chamam mais `update_quotes_for_portfolio` durante requests financeiros.
- `positions` agora é estritamente DB-first e possui gate contra reintrodução de refresh ou dependência de `quotes_service`.
- A auditoria confirmou `rentabilidade` como superfície GET/DB-first e classificou `quotes` como placeholder redundante ainda pendente de prova final de consumidores.
- A matriz `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` foi sincronizada com os achados e decisões deste bloco.

### Corrigido — fronteira opt-in de sincronização de mercado (07/08/2026)

- O CRUD de `transactions` deixou de disparar automaticamente onboarding de mercado e backfill de Proventos após `POST`/`PATCH`.
- Criar ou editar uma transação continua executando apenas efeitos locais necessários: cadastro básico do ativo, atualização derivada de Renda Fixa/Tesouro quando aplicável, invalidação/reconstrução de snapshots e caches.
- Sincronização de preços, logos, eventos corporativos e Proventos volta a pertencer exclusivamente a pipelines operacionais explícitos/opt-in, em conformidade com o gate #227.
- Adicionado gate estrutural que proíbe reintrodução de `asset_onboarding_service`, `dividend_backfill_service` ou `asset_market_pipeline_service` no router de transações.
- `GET /api/v1/prices/{ticker}/history` teve a documentação corrigida para refletir seu comportamento real DB-first; um gate impede imports de providers/backfills no router.
- A matriz `docs/ROUTER_ENDPOINT_AUDIT_2026-08.md` foi expandida com classificação de endpoints operacionais, descoberta/provider, placeholders e compatibilidades.

### Alterado — reorganização de governança e roadmap (07/08/2026)

- A Issue #227 foi atualizada como gate-mãe de estabilização antes de dados reais.
- A Issue #247 passou a executar primeiro a reconciliação de documentação, Issues e PRs e, somente depois, a auditoria técnica de legado, serviços, routers e endpoints.
- As Issues abertas foram classificadas em trabalho atual, bloqueadas/dependentes e backlog para evitar competição de prioridades.
- README, ROADMAP, arquitetura e continuidade agora usam uma única ordem canônica: governança → auditoria → IBOV/TWR → retomada operacional → Metas + Análise.
- Percentuais de progresso foram removidos do ROADMAP quando não representavam uma métrica objetiva verificável.
- A #241 foi removida das pendências: está encerrada, com `goals` preservado como exceção arquitetural deliberada.
- As PRs Dependabot abertas foram separadas do roadmap funcional e devem ser avaliadas individualmente por risco, compatibilidade e CI.
- Nenhuma funcionalidade, migration, schema ou runtime foi alterado neste bloco de governança.

### Alterado — fechamento arquitetural da convergência Alembic/ORM (07/08/2026)

- A Issue #241 passa a considerar concluída a convergência de todos os domínios estabilizados fora de `goals`.
- `goals` foi formalizado como exceção arquitetural consciente: nenhuma migration será criada apenas para silenciar o `alembic check`.
- O redesenho de Metas foi delegado à Issue #246 e deverá evoluir em conjunto com Análise de Carteira (#57).
- README, ROADMAP, arquitetura e checkpoint de continuidade foram sincronizados com essa fronteira.
- `fx_rates` deixou de constar como pendência estrutural e permanece consolidado como contrato DB-first no MetaData.
- A auditoria arquitetural global de serviços, routers, endpoints e legado restante passa a ser o próximo macrobloco antes da promoção estrutural para `main`.

### Corrigido — endurecimento defensivo de timestamps (07/08/2026)

- `users`, `portfolios`, `system_configs`, `fixed_income_investments`, `portfolio_positions` e `portfolio_snapshots` passam a exigir `created_at`/`updated_at NOT NULL` por migrations pequenas e reversíveis.
- Cada upgrade conta previamente linhas nulas e aborta se encontrar qualquer inconsistência; nenhum backfill silencioso é executado.
- O primeiro revision ID do terceiro bloco excedia o `VARCHAR(32)` de `alembic_version` e foi detectado pelo gate global antes da certificação; a revisão foi corrigida para `20260807_pos_snap_ts_nn`.
- O gate específico de timestamps agora também protege explicitamente o limite de 32 caracteres dos revision IDs.
- Documentação técnica do endurecimento e da correção de integridade foi adicionada em `docs/ALEMBIC_TIMESTAMP_HARDENING_2026-08.md`.

### Corrigido — convergência adicional Alembic/MetaData (07/08/2026)

- `portfolio_snapshots` passou a refletir exatamente os comentários físicos da migration `005`; os campos TWR adicionados por `20260713` continuam documentados no código sem inventar comentários de coluna ausentes no banco.
- `asset_dividends` passou a representar `idx_ad_asset_exdate_desc` e `ix_asset_dividends_approved_on`, já existentes pelas migrations `021` e `027`.
- `transactions` passou a representar `ix_transactions_portfolio_id`, os quatro índices da migration `0020` e `idx_txn_portfolio_date_asc` da migration `021`, preservando o contrato financeiro migrado.
- `corporate_events` passou a representar os quatro índices, `uq_corporate_events_source_identity` e `raw_metadata` como JSONB conforme `20260731_corp_event_catalog`.
- `assets` voltou a refletir `updated_at`, `isin_code`, os índices físicos de ISIN/cache/provider, `currency NOT NULL`, os comentários do cache L1 e o nome canônico `uq_asset_ticker_type`.
- Adicionados gates de regressão específicos para snapshots, Proventos, transações, eventos corporativos e ativos.
- Adicionada migration defensiva `20260807_drop_dup_rate_idx` para remover somente o índice único redundante `ix_rate_history_indicator_date_unique` quando o índice canônico `uq_rate_history_indicator_date` estiver presente; nenhuma linha é alterada.

### Corrigido — alinhamento de índices e metadados Alembic/MetaData (07/08/2026)

- `rate_history` passou a representar `uq_rate_history_indicator_date` como índice único, exatamente como a migration `014`, e recuperou os comentários canônicos de `indicator` e `source`.
- `fixed_income_investments` deixou de pedir o índice simples inexistente `ix_fixed_income_investments_portfolio_id` e passou a refletir o comentário canônico de `daily_liquidity` da migration `015`.
- `portfolio_snapshots` passou a representar os três índices de consulta criados pela migration `005`, além do índice DESC já alinhado anteriormente.
- Adicionados gates específicos para `rate_history`, Renda Fixa e snapshots.
- Nenhuma migration, DDL ou dado foi alterado nesses alinhamentos.

### Corrigido — alinhamento de índices Alembic/MetaData (06/08/2026)

- `asset_prices` passou a representar no ORM o índice físico `idx_ap_asset_ts (asset_id, timestamp DESC)`.
- `audit_logs` deixou de pedir índices simples inexistentes em `user_id`/`portfolio_id` e passou a representar os índices compostos com `created_at DESC`.
- `portfolio_snapshots` passou a representar corretamente `idx_ps_portfolio_date_desc`.
- `portfolio_positions` passou a preservar `idx_pp_portfolio` e deixou de pedir índice simples inexistente em `asset_id`.
- `portfolio_class_targets` passou a representar `idx_pct_portfolio`, criado pela migration de performance.
- Adicionados gates para impedir regressão desses contratos de índice.
- Nenhuma migration, DDL ou dado foi alterado nestes alinhamentos.

### Removido — schema mensal legado vazio de IRPF (06/08/2026)

- Adicionadas migrations separadas para `irpf_losses` e `irpf_records`, ambas sem consumidores runtime e vazias na evidência PostgreSQL local.
- Cada upgrade retorna quando a tabela já não existe e bloqueia a contração caso encontre qualquer linha.
- Cada downgrade restaura o contrato original, FK para `users.id` com `ON DELETE CASCADE`, defaults e índices históricos.
- O enum compartilhado `irpfmarket` é preservado e não é removido por nenhuma das duas migrations.
- A contração foi coordenada pela Issue #242, separada dos contratos financeiros compartilhados da #241.

### Removido — contrato legado vazio `goal_allocations` (06/08/2026)

- Adicionada migration isolada para remover `goal_allocations`, tabela sem consumidor runtime e vazia na evidência local.
- O upgrade é bloqueado quando existir qualquer linha, impedindo descarte silencioso de dados.
- O downgrade restaura tabela, FK `goal_allocations_goal_id_fkey` com `ON DELETE CASCADE` e índice `ix_goal_allocations_id`.
- O tratamento de `goal_allocations` não estabiliza o domínio `goals`, que permanece reservado ao redesenho #246/#57.

### Adicionado — fixture sintética transacional para contratos legados (06/08/2026)

- Adicionada fixture PostgreSQL nativa para `irpf_records`, `irpf_losses` e `goal_allocations`, incluindo seus pais `users`, `portfolios` e `goals`.
- A fixture usa `ON_ERROR_STOP`, valida exatamente uma linha por contrato e termina obrigatoriamente em `ROLLBACK`.
- Adicionados gates que proíbem `COMMIT`, `DROP TABLE` e `TRUNCATE`, além de proteger o uso de variáveis `psql` e as três asserções de cardinalidade.
- Nenhuma migration, DDL persistente, tabela ou dado real foi alterado.