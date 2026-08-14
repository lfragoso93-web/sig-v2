# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Alterado — contrato explícito de enriquecimento do asset seed (14/08/2026)

- Renomeado `run_backfill` para `run_market_enrichment` no asset seed, refletindo que a opção controla somente histórico de preços e logos.
- Helper e métrica de resultado também perderam a nomenclatura genérica de backfill; nenhuma semântica de Proventos permanece nessa superfície.
- `system-bootstrap.v4` e seed B3 continuam chamando o catálogo com enriquecimento amplo desabilitado.
- Testes e documentação foram sincronizados e o contrato do bootstrap proíbe a reintrodução do nome legado.

### Alterado — contrato completo de ambiente Docker (14/08/2026)

- Reconstruído `.env.example` a partir das configurações efetivamente consumidas pela aplicação, Docker, frontend e rotinas operacionais.
- Documentados ambiente, portas, banco, Redis, autenticação, CORS, rate limits, SuperAdmin, providers, bootstrap v4 e operações de pré-produção, sempre com gates perigosos desabilitados por padrão.
- `docker-compose.yml` passou a encaminhar `VITE_API_URL` como argumento de build do frontend; vazio preserva o proxy Nginx canônico.
- Adicionado teste de contrato para impedir que novos campos de `Settings` ou variáveis operacionais essenciais deixem de aparecer no exemplo.

### Alterado — pipeline de mercado sem eventos paralelos (14/08/2026)

- Removidos `sync_events`, `events_synced` e o import de `dividend_backfill_service` do pipeline de mercado.
- Asset seed, serviço batch e CLIs de mercado deixaram de expor flags, argumentos, logs ou métricas de eventos/Proventos.
- O pipeline permanece responsável por catálogo, histórico de preços e logo; eventos globais entram exclusivamente pelos estágios gated do `system-bootstrap.v4`.
- Adicionada regressão estrutural cobrindo todas as cinco superfícies contra reintrodução da porta paralela.

### Removido — onboarding órfão de mercado (14/08/2026)

- Removido `asset_onboarding_service.py` após confirmação de ausência de consumidores em runtime, routers, jobs, CLIs e bootstrap.
- O serviço declarava execução após criação de ativo/transação, mas o CRUD já proíbe qualquer ingestão externa automática e mantém somente operações locais e DB-first.
- Adicionado gate de ausência física; pipeline, seed, batch e CLIs foram preservados para uma contração independente da etapa paralela de eventos.

### Removido — sincronizador diário órfão de Proventos (14/08/2026)

- Removidos `proventos_daily_sync_service.py` e seu teste exclusivo após a confirmação de que nenhum runtime, scheduler, CLI, workflow ou serviço ainda os consumia.
- O módulo havia se tornado uma segunda orquestração sem os gates transacionais do seed certificado após a retirada da CLI dedicada e da etapa no full market rebuild.
- O gate do scheduler passou a exigir também a ausência física do módulo, além de proibir seus antigos imports e chamadas.
- Adapters, parsers e persistência compartilhados pelo `pre-prod-dividends-seed.v2` foram preservados.

### Removido — Proventos do full market rebuild (14/08/2026)

- Removida a etapa paralela de Proventos de `full_market_rebuild_service.py`, junto com suas métricas do resumo operacional.
- O caminho antigo chamava o sincronizador diário sem advisory lock dedicado, transação única, rollback integral ou opt-in explícito, contrariando o contrato da #226.
- O `system-bootstrap.v4`, por meio do seed certificado e gated, permanece como única entrada operacional certificável para o domínio.
- Adicionado gate estrutural garantindo que o full rebuild não volte a importar, chamar ou registrar a etapa de Proventos.

### Removido — CLI legada de sincronização de Proventos (14/08/2026)

- Removido `run_proventos_sync.py`, sem consumidores, entry point ou automação no projeto.
- A CLI permitia chamar diretamente `run_backfill` e `run_daily_proventos_sync`, duplicando o bootstrap certificado e contornando seus gates explícitos.
- Adicionado gate estrutural para impedir a reintrodução dessa porta manual; os serviços compartilhados permanecem preservados enquanto seus consumidores e adapters canônicos são auditados.

### Alterado — FX DB-first nos snapshots por classe (14/08/2026)

- `portfolio_class_snapshot_service` deixou de importar `fx_service` e passou a consumir exclusivamente `fx_rates` pelo leitor persistido.
- A cobertura USD-BRL necessária é pré-carregada antes da exclusão/reconstrução dos snapshots; ausência aborta explicitamente o bloco sem provider ou taxa fixa.
- Valores cambiais permanecem em `Decimal` e os snapshots monetários continuam quantizados em R$ 0,01.
- Tesouro Direto e Renda Fixa continuam indisponíveis neste TWR por classe e não tiveram valuation alterado.

### Removido — serviço órfão de posições com provider (14/08/2026)

- Removido `position_service.py`, sem consumidores de produção e duplicado em relação a `portfolio_service`/`canonical_positions_service`.
- Eliminado o único caminho desse serviço que chamava `quotes_service.get_current_price` e convertia ausência de cotação em preço médio silencioso.
- Adicionado gate estrutural para impedir a reintrodução do módulo ou de imports de produção.
- Endpoints públicos, contratos canônicos e comportamento de Tesouro/Renda Fixa não foram alterados.

### Alterado — baseline pós-segurança e retomada da sanitização (14/08/2026)

- PR #271 mergeada e Issue #269 concluída no baseline `4ff76c4fe9f1738db9b392b3568fcb35f81185e7`, alinhando `main` e `stable-15jun` após as correções de SSRF, path injection, dependências vulneráveis, log injection e hardening da imagem.
- #268 concluiu o smoke funcional e o gate global no SHA `a8444b545a10aa7d48dd70f08a07e3fa386605d6`, estabelecendo `test_ready=true` apenas para dados fictícios/descartáveis.
- `ready_for_real_data=false` permanece obrigatório até #226/#216/#158 e decisão formal da #227.
- Branches obsoletas foram removidas após preservação dos snapshots nas tags `archive/recover-snapshot-b1c8080c` e `archive/corporate-actions-5e110967`; branches Dependabot remanescentes seguem fila técnica separada.
- A ordem corrente passa a ser #247 (sanitização residual) → #150 → #149 → #226/#216/#158 → #253/#246+#57.

### Alterado — universo CRIPTO Top 100 por capitalização (11/08/2026)

- Criada a Issue #267 para separar explicitamente catálogo descoberto, universo CRIPTO suportado e histórico certificado.
- O universo operacional de CRIPTO passa a ser a interseção entre as Top 100 por `market_cap_rank` do CoinGecko e os símbolos disponíveis no catálogo CRIPTO da BRAPI.
- CoinGecko é usado somente como fonte de ranking de relevância durante bootstrap/readiness; BRAPI continua sendo a integração de disponibilidade/cotações do SGI.
- O seed CRIPTO deixou de materializar o catálogo BRAPI amplo e agora cria/atualiza somente o universo suportado.
- O estágio `asset_price_history` do `system-bootstrap.v4` limita o backfill CRIPTO ao mesmo universo suportado.
- O readiness CRIPTO passou a contar histórico, duplicidades, statuses bloqueantes, seams e shallow histories somente no universo Top 100 suportado.
- `pre_prod_crypto_seam_audit` e `pre_prod_crypto_shallow_history_audit` receberam filtro opcional de tickers, preservando o comportamento global padrão das CLIs.
- Ativos CRIPTO previamente persistidos fora do universo suportado não são apagados, não têm `provider_status` reescrito e permanecem auditáveis, mas não devem bloquear o novo readiness CRIPTO.
- Adicionados testes do contrato de interseção/deduplicação e gate estrutural do seed.
- README, ROADMAP e `docs/DEVELOPMENT_CONTINUITY.md` foram sincronizados; `ready_for_real_data` permanece `false` até validação operacional e certificação final da #248/#227.

### Alterado — bootstrap v4 com eventos corporativos gated (08/08/2026)

- Criado `system_bootstrap_corporate_events_stage.py` como wrapper dedicado para eventos corporativos globais.
- A execução é fail-closed sem `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS=true`, com gate anterior à abertura de sessão/provider.
- O estágio lê somente ativos elegíveis persistidos (`ACAO`, `BDR`, `ETF_NACIONAL`), adquire advisory lock transacional e delega exclusivamente a `sync_corporate_events_for_asset`.
- O serviço canônico continua responsável pela coleta/normalização/persistência e executa apenas `flush`; o wrapper controla commit único e rollback integral do estágio.
- `asset_market_pipeline_service` e `dividend_backfill_service` não participam do novo caminho; a mistura legada de `events_synced`/Proventos permanece registrada para auditoria separada.
- Adicionados testes dirigidos de gate, ordem do lock, filtro DB-first, commit, rollback/stop e relatório determinístico.
- O orquestrador evoluiu para `system-bootstrap.v4` e passou a registrar `corporate_events` após `asset_dividends`, mantendo fail-fast e `certified_for_real_data=false`.
- Nenhum provider real foi executado durante estes blocos; a integração é estrutural e ainda depende de validação local integrada/certificação final.
- README, ROADMAP, arquitetura, continuidade e Issues #254/#250/#248/#129 foram sincronizados com o estado v4.

### Alterado — bootstrap v3, FX certificado e Proventos gated (08/08/2026)

- O checkpoint `0e8d96c081a0e788a9edcf69901a134b29b7f696` foi certificado localmente pelo usuário com build Docker aprovado, 22/22 testes dirigidos, `compileall` e import integral de `app.main` aprovados.
- O bootstrap passou a exigir identidade auditável compartilhada (`run_id`, branch `stable-15jun` e SHA completo); o disparo administrativo exige o SHA e o startup pode recebê-lo por `SGI_BOOTSTRAP_COMMIT_SHA`.
- O contrato `system-bootstrap.v2` incorporou câmbio USD-BRL reutilizando o seed transacional PTAX já certificado pela #217, com cobertura própria desde `1994-07-01` e sem fallback BRAPI/AwesomeAPI/fixo.
- A cobertura temporal deixou de ser um parâmetro global: cada domínio define sua maior janela válida conforme a fonte canônica.
- O contrato evoluiu para `system-bootstrap.v3` com etapa explícita `asset_dividends`, reutilizando `pre-prod-dividends-seed.v2` e os adapters estritos BRAPI/Yahoo já existentes.
- Proventos permanecem fail-closed: sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, a etapa aborta antes de consultar providers; esse opt-in técnico não substitui a autorização operacional exigida pela #226.
- O estágio de Proventos escreve exclusivamente em `asset_dividends`, não utiliza `dividend_backfill_service` e não materializa direitos por carteira.
- `ready_for_real_data` permanece `false`; eventos corporativos eram o próximo domínio obrigatório do bootstrap antes da evolução para v4.
- README, ROADMAP, arquitetura, continuidade e Issues #248/#250/#226 foram sincronizados com o novo estado.

### Alterado — readiness, lacuna pontual e catálogo DB-first (07/08/2026)

- O checkpoint `113281b7a0153f02007d6d49761be8fef91d77a8` foi certificado localmente com 26/26 testes, `compileall` e import integral de `app.main` aprovados.
- A Issue #249 foi concluída: `/health` representa liveness/dependências e `/ready` representa readiness operacional, mantendo `ready_for_real_data=false` enquanto o bootstrap global da #248 não estiver completo e certificado.
- Criado `price_date_gap_resolver_service.py` como única exceção dedicada para cotação histórica ausente: leitura DB-first inicial, janela externa limitada a `target_date - 5 dias .. target_date`, persistência em `asset_prices` e nova leitura DB-first.
- `get_price_at_date()` permanece leitor puro e não importa o resolvedor; o fallback pontual não usa `period=max`, backfill global ou `stale_snapshot`.
- Criado `asset_catalog_query_service.py` para sugestões e busca de Tesouro exclusivamente sobre o catálogo persistido pelo bootstrap.
- `assets.py` deixou de importar providers diretamente para catálogo e histórico: `/suggest` e `/tesouro/search` são DB-first; histórico em `/quote/{ticker}` e `/tesouro/price` usa o resolvedor pontual; apenas cotação atual/intraday continua passando pela fachada canônica de preços.
- Ativos desconhecidos não são mais descobertos implicitamente por provider durante requests; precisam existir no catálogo persistido.
