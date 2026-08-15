# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para iniciar ou retomar qualquer conversa de desenvolvimento. Atualizado em 14/08/2026.

## Contexto permanente

- Repositório: `lfragoso93-web/sig-v2`.
- Branch obrigatória: `stable-15jun`; nunca desenvolver diretamente na `main`.
- Confirmar o HEAD remoto e a árvore limpa antes de cada bloco.
- Dividir macroblocos em commits pequenos, independentes e rastreáveis.
- Antes de alterar, revisar Issue, arquitetura, contratos canônicos, consumidores e legado.
- Ao final informar resumo técnico, impacto arquitetural, arquivos, testes, SHA completo, Issue/documentação e próximo bloco.
- `goals` permanece fora da estabilização corrente e não recebe migration apenas para limpar Alembic.

## Baseline confirmado

- `main` = `stable-15jun` em `4ff76c4fe9f1738db9b392b3568fcb35f81185e7`.
- PR #271 mergeada; Issue #269 concluída.
- #268 concluída no checkpoint funcional `a8444b545a10aa7d48dd70f08a07e3fa386605d6`.
- `test_ready=true`: permitido testar somente com dados fictícios/descartáveis.
- `ready_for_real_data=false`: usuários, carteiras, CSV, seeds e snapshots reais continuam bloqueados.
- Snapshots de branches removidas preservados em:
  - `archive/recover-snapshot-b1c8080c`;
  - `archive/corporate-actions-5e110967`.
- Branches remanescentes: `main`, `stable-15jun` e cinco branches Dependabot sob triagem separada.

## Evidência do gate `test_ready`

No fechamento da #268:

- backend completo em Linux/Python 3.12: **1638 passed, 0 failed**;
- smoke HTTP e cleanup descartável aprovados;
- classes canônicas, BTC elegível e blockers CRIPTO exercitados;
- Alembic/drift gate, mypy, flake8, `compileall` e `app.main` aprovados;
- frontend lint, typecheck, 93 testes e build aprovados;
- CI aprovou backend, frontend, pip/npm audit, Trivy filesystem, Gitleaks e lint dos Dockerfiles;
- nenhum provider foi observado nos requests financeiros auditados.

A #269/#271 acrescentou hardening de SSRF, path injection, dependências, logs e imagem. O PR registrou backend **1.673 passed, 24 skipped**, frontend **93 testes**, `npm audit` sem vulnerabilidades e import/build aprovados.

## Arquitetura que deve ser preservada

- Runtime financeiro é DB-first; provider não participa de GETs/cálculos financeiros.
- Providers pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados.
- Preços externos são persistidos antes do consumo financeiro.
- Ausência de preço/FX é explícita; não vira zero, preço médio, taxa `1.0` ou fallback silencioso.
- `summary.v2`, `rentabilidade.v2`, projetores de posição/custo e snapshots são contratos canônicos.
- Proventos pertencem ao ativo em `asset_dividends`; direitos por carteira são calculados sob demanda.
- Eventos corporativos pertencem ao ativo em `corporate_events`; transações históricas não são mutadas.
- Não reintroduzir `AppConfig`, `IRPFReport`, `Dividend/dividends` ou materialização de proventos por carteira.
- Tesouro/Renda Fixa devem preservar marcação a mercado; evolução de TWR pertence à #149.

## Trabalho corrente — #247

### 247-A — governança e documentação

- sincronizar README, ROADMAP, CHANGELOG, arquitetura e este documento;
- atualizar #227 para `test_ready=true` e baseline pós-#271;
- reclassificar Issues abertas e remover dependências/status obsoletos;
- consolidar #248/#250 no gate operacional da #227 quando o histórico estiver preservado;
- tratar #129 como residual da #247;
- auditar #83 contra a implementação existente antes de decidir fechamento;
- manter PRs/branches Dependabot como fila técnica separada.

### 247-B — posições DB-first

- concluído: `position_service.py` não possuía consumidores de produção;
- removidos o serviço órfão e seu teste exclusivo;
- eliminado o caminho `quotes_service.get_current_price` e o fallback silencioso por preço médio;
- gate estrutural protege a ausência do módulo e de imports futuros;
- endpoints públicos continuam em `portfolio_service`/`canonical_positions_service`.

### 247-C — snapshots de classe / FX DB-first

- concluído: `portfolio_class_snapshot_service` usa `fx_rate_reader` DB-only;
- cobertura USD-BRL é pré-carregada antes de qualquer exclusão/rebuild;
- ausência persistida falha explicitamente, sem BCB/AwesomeAPI/taxa fixa;
- valores permanecem em `Decimal` e quantizados em R$ 0,01;
- TWR/valuation de Tesouro e Renda Fixa não foram alterados.

Commits publicados:

- `6a279206c3975407a7aa7c187e8c9e762a761392` — gate DB-first;
- `7fe02fee738539d8ec9555b7b727b388a67df215` — implementação e testes comportamentais.

### 247-D — Proventos e eventos

- auditar `proventos_daily_sync_service.py`, `asset_market_pipeline_service.py`, `dividend_backfill_service.py` e `run_proventos_sync.py`;
- eliminar ou confinar portas paralelas, preservando uma entrada canônica de bootstrap;
- usar a tag arquivada de corporate actions apenas como evidência para decisões de backlog;
- testar locks, transação, idempotência e ausência de consumers/imports legados.

Primeiro recorte concluído:

- `run_proventos_sync.py` não possuía consumidor, entry point ou automação;
- a CLI foi removida porque expunha `run_backfill` e `run_daily_proventos_sync`
  fora dos gates do `system-bootstrap.v4`;
- uma regressão estrutural impede a reintrodução dessa porta manual;
- os três serviços restantes continuam em auditoria e não devem ser removidos
  antes da separação entre adapters canônicos e orquestrações legadas.

Segundo recorte concluído:

- removida do `full_market_rebuild_service.py` a etapa paralela de Proventos e
  suas métricas operacionais;
- o rebuild não importa nem chama `proventos_daily_sync_service.py`;
- o contrato da #226 e o `system-bootstrap.v4` permanecem como única entrada
  operacional certificável para o domínio;
- `proventos_daily_sync_service.py` ficou sem consumidor de produção e deve ser
  avaliado isoladamente no próximo recorte.

Terceiro recorte concluído:

- removidos `proventos_daily_sync_service.py` e seu teste exclusivo após nova
  confirmação de ausência de consumidores de produção;
- scheduler, bootstrap e full rebuild permanecem protegidos contra imports da
  orquestração removida;
- o gate do scheduler agora também exige a ausência física do módulo;
- adapters e persistência usados pelo seed certificado não foram alterados.

Quarto recorte concluído:

- removido `asset_onboarding_service.py` após confirmação de zero consumidores;
- o CRUD de transações continua criando apenas o registro local do ativo,
  invalidando cache e recalculando snapshots, sem BackgroundTask de provider;
- pipeline de mercado, seed, batch e CLIs foram preservados para a retirada
  independente da etapa paralela de eventos no próximo recorte.

Quinto recorte concluído:

- removidos `sync_events`, `events_synced` e `run_backfill` do pipeline de
  mercado e de todos os seus callers;
- seed, batch e CLIs de mercado ficaram limitados a catálogo, preços e logo;
- eventos e Proventos passam exclusivamente pelos estágios gated do
  `system-bootstrap.v4`;
- regressão estrutural protege as cinco superfícies contra reintrodução.

Configuração operacional sincronizada:

- `.env.example` cobre todos os campos de `Settings`, Docker, frontend,
  bootstrap e operações controladas de pré-produção;
- gates de bootstrap permanecem desabilitados por padrão; o router de debug foi
  removido no décimo terceiro recorte;
- Compose encaminha `VITE_API_URL` ao build do frontend;
- teste estrutural impede nova deriva entre código e exemplo de ambiente.

Sexto recorte concluído:

- `run_backfill` foi renomeado para `run_market_enrichment` no asset seed;
- helper e métrica passaram a representar explicitamente preços/logos, sem
  semântica residual de Proventos;
- bootstrap e seed B3 continuam desabilitando esse enriquecimento amplo;
- testes protegem o bootstrap contra reintrodução do nome legado.

Sétimo recorte concluído:

- removidos `market_pipeline_batch_service.py`, `run_market_pipeline.py` e
  `run_market_pipeline_batch.py`, sem consumidores de runtime ou runbooks;
- removido o teste exclusivo que legitimava o batch paralelo;
- gates estruturais exigem a ausência física das três portas;
- `asset_market_pipeline_service.py` foi preservado temporariamente porque o
  enriquecimento opcional do asset seed ainda o referencia.

Oitavo recorte concluído:

- removido o enriquecimento opcional de preços/logos do asset seed;
- simplificada `run_asset_seed` para catálogo e metadados fornecidos pela fonte;
- removido `asset_market_pipeline_service.py` após confirmação de zero
  consumidores remanescentes;
- históricos de preços, Proventos e eventos permanecem nos estágios dedicados
  do `system-bootstrap.v4`.

Nono recorte concluído:

- removido `run_backfill` de `dividend_backfill_service.py`, sem consumidores;
- gate estrutural impede a reintrodução do wrapper genérico;
- `ParsedDividendEvent`, parser e fetchers usados pelo seed certificado foram
  preservados sem alteração;
- `backfill_dividends` permanece temporariamente para separação em recorte
  próprio, pois ainda possui cobertura legada direta.

Décimo recorte concluído:

- criado `dividend_event_normalizer.py` com `ParsedDividendEvent` e
  `parse_dividend_event`;
- collector, persistência e testes do seed certificado deixaram de importar
  modelo/parser do backfill legado;
- `dividend_backfill_service.py` passou a consumir o normalizador neutro;
- gate estrutural proíbe SQLAlchemy, HTTP e dependência reversa no normalizador;
- regras de datas, tipos, valores e payload bruto foram preservadas.

Décimo primeiro recorte concluído:

- criado `dividend_brapi_payload.py` para interpretar respostas de ações e FIIs;
- o adapter BRAPI certificado deixou de importar o backfill legado;
- o serviço legado passou a consumir a mesma fronteira neutra, sem mudança de
  endpoint, filtro por ticker ou categorização dos eventos;
- gate estrutural proíbe HTTP, SQLAlchemy e dependência reversa no parser;
- `backfill_dividends` ficou isolado para decisão de remoção no próximo recorte.

Décimo segundo recorte concluído:

- removidos `backfill_dividends` e `dividend_backfill_service.py` após a
  confirmação de ausência de consumidores de runtime;
- removidos os testes exclusivos que legitimavam a porta legada;
- as nove regras úteis do parser foram migradas para a suíte unitária do
  normalizador canônico;
- preservado o teste financeiro DB-first de eventos não monetários;
- gate estrutural passou a exigir a ausência física do serviço removido.

Décimo terceiro recorte concluído:

- removido o router de debug, sem consumidores, que expunha listagem de usuários,
  redefinição de senha e criação de `superadmin` por segredo estático paralelo;
- removidas a montagem condicional e as configurações órfãs `ADMIN_SECRET` e
  `DEBUG_RATE_LIMIT`;
- operações administrativas legítimas permanecem em `/admin`, protegidas por
  JWT e `require_superadmin`;
- gate estrutural impede a reintrodução do arquivo, rota ou configuração.

Décimo quarto recorte concluído:

- removido `frontend/src/App.tsx`, que continha apenas `export {}` e não possuía
  imports, testes ou participação no build;
- `frontend/src/main.tsx` permanece a única entrada React, responsável por
  providers, router e montagem no DOM;
- gate estrutural exige a ausência do arquivo legado e o contrato mínimo da
  entrada canônica.

Décimo quinto recorte concluído:

- removidos placeholders órfãos de Análise e Histórico, stubs antigos de
  Login/Register, router alternativo e `ProtectedRoute` duplicado;
- `main.tsx`, `router/ProtectedRoute.tsx` e páginas `auth/*` permanecem como
  superfícies canônicas;
- `MetasPage.tsx` foi preservada sem alterações funcionais, sob o bloqueio
  explícito do macroprojeto #246 + #57;
- gate estrutural protege a ausência dos seis arquivos e a presença das
  entradas canônicas.

Décimo sexto recorte concluído:

- removida do menu de posições a ação “Análise do Ativo”, que navegava para
  `/carteira/analise` sem existir rota correspondente;
- ações válidas de adicionar e consultar lançamentos foram preservadas;
- teste do menu exige somente as duas ações funcionais e a ausência do link;
- nenhuma implementação de Análise foi iniciada; #57 permanece bloqueada.

Décimo sétimo recorte concluído:

- `main.tsx` passou a importar diretamente a visão consolidada canônica de
  Patrimônio e o re-export intermediário foi removido;
- as subrotas de renda variável, Tesouro e renda fixa foram registradas como
  rotas diretas, pois a página consolidada não possui `<Outlet>`;
- `/carteira/patrimonio` continua exibindo a visão consolidada, enquanto as
  três URLs específicas agora podem renderizar seus componentes;
- gate estrutural protege import, ausência do alias e registro das subrotas.

Décimo oitavo recorte concluído:

- redirects `/metas` e `/irpf` foram auditados e preservados como compatibilidade
  unidirecional para `/carteira/metas` e `/carteira/irpf`;
- ambos usam `Navigate replace`, não possuem página, loader, escrita ou cálculo
  próprio e não são usados pela navegação interna;
- teste estrutural protege esse confinamento;
- remoção futura exige evidência de desuso de URLs externas; #246/#57 não foram
  iniciadas nem alteradas.

Décimo nono recorte concluído:

- removidos dois `except Exception: pass` redundantes das invalidações de cache
  em atualização e exclusão de carteira;
- ambas delegam diretamente a `cache_delete`, cuja fronteira Redis já é
  deliberadamente fail-open;
- comportamento de request, persistência e disponibilidade não mudou;
- gate AST exige duas invalidações e ausência de captura silenciosa local.

Vigésimo recorte concluído:

- a fronteira Redis permanece opcional e fail-open, mas suas cinco capturas
  amplas deixaram de ser silenciosas;
- falhas de conexão, leitura, escrita e exclusão registram operação, chave ou
  padrão sanitizado, tipo e mensagem sanitizada da exceção;
- valores de cache nunca são enviados ao log;
- gate AST impede `pass` nos handlers e protege sanitização/observabilidade.

Vigésimo primeiro recorte concluído:

- a confirmação remota do onboarding deixou de ser capturada silenciosamente;
- falha no `PATCH /users/me/onboarding` mantém o usuário na tela e apresenta
  erro recuperável, sem navegar com estado local incoerente;
- se a carteira já foi criada, a nova tentativa repete somente a confirmação
  idempotente e não cria uma carteira duplicada;
- teste estrutural protege persistência, refresh, mensagem e retry seguro.

Vigésimo segundo recorte concluído:

- `useTickerQuote` deixou de converter falhas de rede/servidor em ausência
  silenciosa de erro;
- 404 apresenta ativo ausente no catálogo; demais falhas apresentam erro
  recuperável de consulta, já consumido pelo modal de transação;
- mensagem deixou de expor o nome do provider, preservando a abstração pública;
- removido `any` do catch e adicionado teste estrutural do contrato.

Vigésimo terceiro recorte concluído:

- buscas de ativos/Tesouro e preço histórico de título continuam fail-soft,
  mas agora retornam erro explícito além de lista/preço vazio;
- o modal de transação consolida e apresenta uma mensagem provider-neutral;
- indisponibilidade deixa de ser confundida com “nenhum resultado” e preço de
  Tesouro pode ser informado manualmente após falha;
- teste estrutural cobre os três hooks e o consumidor.

Vigésimo quarto recorte concluído:

- `fx_service.py` foi reduzido à única responsabilidade ainda consumida: o
  UPSERT transacional de USD/BRL usado pelo bootstrap;
- removidas APIs de leitura órfãs que faziam I/O BCB/AwesomeAPI em request e
  podiam fabricar taxa fixa `5.70`;
- consumidores financeiros continuam nos readers DB-first dedicados;
- gate estrutural impede a reintrodução de provider, fallback ou API de leitura
  nesse módulo de persistência.

Vigésimo quinto recorte concluído:

- o reader DB-first usado por resumo e snapshot deixou de retornar USD/BRL fixo
  `5.70` quando `fx_rates` não possui cobertura;
- ausência persistida agora falha explicitamente e identifica a data efetiva,
  sem provider, escrita ou valor financeiro inventado;
- a semântica válida de usar a última taxa persistida até a data foi preservada;
- testes protegem ausência de fallback e o erro de cobertura vazia.

Vigésimo sexto recorte concluído:

- removido `rf_calc_service.py`, serviço duplicado sem consumidor de runtime,
  testes, CLI, scheduler ou bootstrap;
- o legado abria sessões próprias e podia consultar BRAPI durante valuation em
  request, contrariando a fronteira DB-first;
- `fixed_income_valuation_service.py` permanece como única implementação de
  renda fixa efetivamente consumida;
- gate estrutural impede a restauração do serviço e de seus símbolos públicos.

Vigésimo sétimo recorte concluído:

- `_fetch_prices_batch` deixou de transformar falha do reader/banco em mapa
  vazio, que era indistinguível de ausência real de preços;
- erros de infraestrutura agora são propagados até a fronteira HTTP;
- cobertura parcial legítima continua sendo representada pelo reader DB-first;
- teste protege a diferença entre falha de consulta e cotação ausente.

### 247-E — superfícies sensíveis e frontend legado

- router de debug removido no décimo terceiro recorte;
- `frontend/src/App.tsx` removido no décimo quarto recorte;
- placeholders e módulos frontend órfãos removidos; aliases, redirects e catches
  amplos seguem para recortes próprios;
- preservar #246 + #57 como macroprojeto bloqueado.

### 247-F — gate global

- backend: pytest completo, flake8, mypy, compile/import e Alembic/drift;
- frontend: lint, typecheck, testes e build;
- segurança: npm/pip audit, Gitleaks e Trivy;
- smoke HTTP fictício, cleanup e inspeção de provider;
- concluir #247/#129 e preparar PR `stable-15jun` → `main` somente com tudo verde.

## Ordem após a sanitização

1. #150 — histórico persistido do IBOV.
2. #149 — TWR de Tesouro Direto/Renda Fixa com marcação a mercado persistida.
3. #226 — duas execuções reais controladas de Proventos, somente com autorização operacional específica.
4. #216 — fechar gate agregado de seeds/bootstrap.
5. #158 — CSV, posições, snapshots e reconciliação da primeira base real.
6. Decidir formalmente `ready_for_real_data=true` na #227.
7. #253 — Central de Bootstrap SuperAdmin.
8. #246 + #57 — Metas + Análise como macroprojeto único.

## Prompt mínimo para retomada

```text
@GitHub Continue o SGI v2 seguindo docs/DEVELOPMENT_CONTINUITY.md.

Repo: lfragoso93-web/sig-v2
Branch exclusiva: stable-15jun
Baseline: 4ff76c4fe9f1738db9b392b3568fcb35f81185e7
Gate-mãe: #227
Trabalho atual: #247

Estado:
- test_ready=true;
- ready_for_real_data=false;
- preservar DB-first e contratos canônicos;
- commits pequenos e documentação/Issues vivas.

Próxima ação: continuar do primeiro sub-bloco pendente da #247.
```
