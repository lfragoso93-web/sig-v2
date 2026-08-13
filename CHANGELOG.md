# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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
