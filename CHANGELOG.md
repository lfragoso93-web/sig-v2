# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Alterado — rebaseline pós-merge PR #302 (01/09/2026)

- Registrado que a PR #302 foi mergeada em `main` pelo commit `7861268a2528d80e8c23dfc55f7b0800402abc6d`.
- `stable-15jun` segue como branch obrigatória de desenvolvimento em `2c9358629b3e5e9206a365ebeac45f9272dfd48e`.
- Documentada a diferença esperada: `main` está um commit à frente apenas pelo merge commit da #302.
- Inventário de PRs abertas atualizado para Dependabot #295, #296, #297, #298, #299, #300 e #301.
- Mantida a regra operacional de evitar PRs para microblocos e promover apenas macroblocos validados.

### Alterado — IBOV persistido DB-first (#150)

- O rebuild histórico B3/COTAHIST passa a garantir o ativo sintético `IBOV` como benchmark persistido em `assets`.
- Fechamentos do `IBOV` vindos de COTAHIST são persistidos em `asset_prices` com `source=b3_cotahist`, sem provider em runtime financeiro.
- O relatório do estágio B3 passa a incluir o benchmark sintético nas contagens operacionais de ativos/preços.
- A leitura mensal de benchmarks em Rentabilidade compara datas de `asset_prices.timestamp` por dia calendário, evitando excluir o fechamento do próprio `end_date`.
- Nenhum seed real, CSV, snapshot, full rebuild real ou `ready_for_real_data=true` foi executado.

### Alterado — Dependabot security-actions (#301)

- Absorvida em `stable-15jun` a atualização `hadolint/hadolint-action` de `v3.4.0` para `v3.5.0` nos jobs Dockerfile lint do CI.
- PR #301 pode ser encerrada após confirmação do commit remoto em `stable-15jun`, sem abrir PR individual.

### Alterado — Dependabot backend security (#298)

- Absorvida em `stable-15jun` a atualização `cryptography` de `50.0.0` para `50.0.1` no backend.
- PR #298 pode ser encerrada após validação local/container e push do commit, sem PR individual.

### Alterado — Dependabot react-stack (#295)

- Absorvida em `stable-15jun` a atualização `@types/react-dom` de `19.2.4` para `19.2.5` no frontend.
- PR #295 pode ser encerrada após validação frontend e push do commit, sem PR individual.

### Alterado — B3 COTAHIST-first para catálogo e OHLCV (29/08/2026)

- O parser COTAHIST passou a sustentar um classificador B3 puro e determinístico para `ACAO`, `FII`, `ETF_NACIONAL` e `BDR`, rejeitando instrumentos inelegíveis e preservando `UNRESOLVED` em ambiguidades.
- Adicionado upsert conservador de catálogo B3 mínimo a partir de COTAHIST, sem BRAPI/Yahoo, banco externo ou migrations novas.
- O estágio B3 de pré-produção passou a montar o catálogo por COTAHIST antes do histórico quando `include_catalog=true`.
- O rebuild histórico B3 passou a persistir `open`, `high`, `low`, `close`, `volume` e `source=b3_cotahist` a partir de `CotahistRecord` com `Decimal`, preservando precedência do mercado à vista sobre fracionário.
- O seed BRAPI deixou de criar ativos B3 ausentes do baseline COTAHIST e passou a atuar como enriquecimento conservador de ativos B3 já persistidos.
- O `system-bootstrap.v4` ganhou estágio explícito `b3_baseline` antes de `asset_catalog`; o início histórico pode ser configurado por ambiente e o fim é sempre o dia atual.
- A CLI auditável `pre_prod_b3_seed` passou a derivar `--end-year` e `--cutoff-date` do dia atual quando não informados, preservando overrides explícitos.
- `CODBDI` continua fora do DTO mínimo; FII x ETF sem sinal seguro permanece `UNRESOLVED`.
- Nenhum seed real de Proventos, CSV, snapshot, migration física, full market rebuild real ou `ready_for_real_data=true` foi executado.

### Alterado — Proventos BRAPI authoritative / Yahoo fallback-only (30/08/2026)

- O coletor estrito de Proventos passou a interromper a cadeia quando BRAPI possui cobertura válida, inclusive resposta vazia com cobertura.
- Yahoo/yfinance só pode atuar depois de BRAPI declarar ausência real de cobertura; tentativa de usar Yahoo antes dessa condição passa a ser bloqueante.
- A persistência global passou a rejeitar defensivamente coleções com linhas normalizadas simultâneas de BRAPI e Yahoo no mesmo ativo.
- Caminhos internos obsoletos de reconciliação complementar/cross-source via Yahoo foram removidos da persistência.
- O runbook e o wrapper OCI de contratos de Proventos foram alinhados para cobrir explicitamente o boundary Yahoo fallback-only.
- O contrato documental de Proventos foi atualizado para remover a semântica de fonte concorrente/complementar.
- As suítes unitárias de coletor, persistência e semântica foram atualizadas para o modelo fallback-only.

### Alterado — rebaseline para certificação OCI e testes integrados (27/08/2026)

- O projeto entrou formalmente em fase de certificação operacional: novas funcionalidades ficam subordinadas à conclusão dos gates de teste e readiness.
- Roadmaps de lab/testes foram atualizados em 31/08/2026 com 7 PRs abertas, 18 Issues abertas e a previsão de entrada em testes integrados com dados descartáveis após três gates verdes.
- Baseline de retomada registrado: `stable-15jun` em `a889edb6bbbb78feb7787c21b3439a0b835b73c6` e `main` em `3eeca232a8627f4562544739112d1dde82b879fb`.
- PRs #290, #291 e #292 passam a compor o baseline de laboratório OCI: build frontend, Cloudflare HTTP/2 200, smoke OCI e validação repetível dos contratos de bootstrap sem seeds reais.
- Evidências de contrato registradas: FX/Macro/Tesouro `81 passed, 1 skipped`; B3/Asset Bootstrap/System Bootstrap `70 passed`; Proventos `93 passed, 8 skipped`.
- O smoke HTTP descartável passou a validar também o gate de SuperAdmin em `/api/v1/admin/bootstrap/status`, exigindo `403` para usuário comum.
- `test_ready=true` permanece válido para dados fictícios/descartáveis; `ready_for_real_data=false` permanece obrigatório.
- Ordem canônica atual: certificar lab e persistência → revalidar #227/#226/#216/#158 → executar operações reais somente quando autorizadas → reconciliar → GO/NO-GO.
- A PR Dependabot #289, TypeScript 7, permanece bloqueada por incompatibilidade com `typescript-eslint 8.67.0` e não deve ser mergeada no estado atual.
- README, ROADMAP e `docs/DEVELOPMENT_CONTINUITY.md` foram sincronizados com este rebaseline.

### Alterado — baseline pós-segurança e gate para teste real (18/08/2026)

- A sanitização arquitetural da #247 foi consolidada como concluída e promovida pela PR #281.
- O bloco final de segurança da #269 foi promovido pela PR #282, cobrindo confinamento de paths de backup, sanitização residual de logs e publicação SARIF do Trivy da imagem backend.
- `test_ready=true` permanece preservado; `ready_for_real_data=false` continua obrigatório.
- A Issue #227 passa a refletir o novo foco: revalidar #226/#216/#158 e executar o TESTE REAL controlado somente quando os gates formais permitirem.
- README, ROADMAP e `docs/DEVELOPMENT_CONTINUITY.md` foram sincronizados para remover o estado obsoleto que ainda tratava a #247 como trabalho corrente.
- O `Security deep scan` continua sendo verificação periódica semanal/manual; a documentação não presume execução de scanners sem evidência explícita.

### Alterado — composição explícita do full market rebuild (15/08/2026)

- `full_market_rebuild_canonical_service.py` deixou de alterar temporariamente funções internas do orquestrador base por monkey-patching.
- `full_market_rebuild_service.py` passou a receber explicitamente as operações de Tesouro, snapshots e leitura do resumo, preservando defaults e ordem das etapas.
- A CLI canônica permanece em `python -m app.cli.full_market_rebuild`; nenhum rebuild, provider ou dado real foi executado durante a refatoração.
- Adicionado gate estrutural contra a reintrodução de mutação global entre as duas camadas.

### Removido — exemplo de ambiente paralelo e desatualizado (15/08/2026)

- Removido `backend/.env.example`, que duplicava o contrato canônico da raiz e ainda documentava `DEBUG_RATE_LIMIT`, `ADMIN_SECRET`, router de debug e fallback via yfinance já removidos.
- `.env.example` da raiz permanece como fonte única para aplicação, Docker Compose, frontend, bootstrap e operações controladas.
- Adicionado gate estrutural exigindo a presença do exemplo canônico e a ausência do duplicado no backend.

### Removido — hooks residuais sem consumidores (15/08/2026)

- Removidos `useAssets`, `useFxRate`/`useUsdBrl` e `assetService`, sem consumidores após a limpeza das páginas paralelas.
- Leituras financeiras ativas continuam pelos readers/hooks específicos e DB-first.
- O inventário de imports do frontend passou a apontar somente `test/setup.ts`, entrada configurada do Vitest, sem candidatos órfãos de runtime conhecidos.

### Removido — implementação duplicada do logo (15/08/2026)

- Removido `SigLogo`, SVG sem consumidores que duplicava a marca ativa.
- `LogoSGI` permanece como implementação única, montada no Topbar e no layout de autenticação.
- Gate estrutural protege a ausência da duplicata e as duas montagens canônicas.

### Removido — formulário paralelo de transações (15/08/2026)

- Removido `TransactionForm`, componente de 397 linhas sem consumidor.
- `AddTransactionModal` permanece como superfície única, com criação e atualização pelos hooks canônicos.
- Gate estrutural protege a ausência do formulário paralelo e a montagem global do modal ativo.

### Removido — visualizações legadas de dividendos (15/08/2026)

- Removidos `DividendChart` e `DividendTable`, sem consumidores e ligados ao contrato antigo de dividendos.
- A página ativa de Proventos preserva donut, histórico mensal e tabela canônica de direitos recebidos.
- Gate estrutural protege a ausência das visualizações paralelas e os três componentes ativos.

### Removido — componentes órfãos de dashboard (15/08/2026)

- Removidos gráfico de alocação, treemap de concentração e modal de carteira sem consumidores.
- Preservados `AssetDonutChart`, distribuição por metas e criação de carteira na Sidebar como superfícies ativas.
- Gate estrutural impede restauração das duplicatas sem montagem.

### Removido — páginas não roteadas de Ativos e Lançamentos (15/08/2026)

- Removidas `AssetsPage` e `LancamentosPage`, sem rota, menu ou consumidor.
- `LancamentosPage` duplicava a página canônica `Transacoes`, que permanece em `/carteira/transacoes`.
- Uma futura gestão do catálogo de ativos deverá ser implementada por issue e rota explícitas; gate protege a ausência das páginas invisíveis.

### Removido — serviços HTTP frontend órfãos (15/08/2026)

- Removidos seis módulos sem consumidores para transações, autenticação, câmbio, metas de classe, performance e metas.
- Hooks/contextos canônicos foram preservados e passam a ser as únicas entradas HTTP dessas áreas.
- Eliminadas também URLs mortas com prefixo `/api/v1` duplicado; gate estrutural protege ausências e entradas válidas.

### Alterado — erros HTTP restantes sem `any` no frontend (15/08/2026)

- Recuperação de senha, atualização de perfil e troca de senha usam extração tipada de detalhe Axios.
- Removidos os três últimos `catch any` ativos do frontend sem alterar os fallbacks específicos das telas.
- A fronteira compartilhada passou a expor separadamente detalhe HTTP textual e mensagem completa.

### Removido — modais paralelos de lançamento (15/08/2026)

- Removidos `ModalNovaTransacao` e `ModalNovoProvento`, sem consumidores no frontend.
- Removido o hook órfão de criação manual de proventos; leituras canônicas permanecem disponíveis.
- O lançamento de transações continua no `AddTransactionModal`; proventos permanecem derivados dos eventos canônicos persistidos.

### Alterado — erros tipados na importação CSV (15/08/2026)

- Validação e importação CSV deixaram de usar `catch any` e acesso inseguro ao payload Axios.
- Listas de validação FastAPI são convertidas explicitamente pelas mensagens `msg`, sem `[object Object]`.
- A fronteira compartilhada preserva detalhes textuais, erros nativos e fallback.

### Alterado — erros Axios tipados no fluxo de Tesouro (15/08/2026)

- Criada fronteira reutilizável para extrair `detail` textual de erros Axios sem `any`.
- Carregamento e exclusão de Tesouro usam `unknown`, preservando mensagem da API, erro nativo e fallback seguro.
- Testes unitários cobrem detalhe HTTP, erro nativo e payload desconhecido/estruturado.

### Corrigido — falhas de proventos não convertidas em zero (15/08/2026)

- As três agregações canônicas de proventos da carteira deixaram de converter erro SQL/dado inválido em `0.0` ou mapa vazio.
- Falhas do reader agora são propagadas; zero permanece reservado a uma agregação válida sem direitos recebidos.
- Testes cobrem as três fronteiras e impedem nova captura local.

### Corrigido — conversão cambial fiscal DB-first (15/08/2026)

- O cálculo legado de ganhos de capital deixou de consultar `USDBRL=X` por `price_history_service` com sessão nula.
- Operações internacionais usam a última USD/BRL persistida até a data da transação, com a sessão do cálculo.
- Ausência de cobertura deixa de assumir paridade `1.0` e falha explicitamente para não distorcer imposto.

### Corrigido — falha de preços persistidos não mascarada (15/08/2026)

- A leitura em lote de preços da carteira deixou de converter erro de banco em mapa vazio.
- Falha de infraestrutura agora é propagada; somente ausência real de uma cotação permanece representada como preço indisponível.
- Teste protege a distinção entre indisponibilidade do banco e cobertura parcial legítima.

### Removido — calculadora legada e órfã de renda fixa (15/08/2026)

- Removido `rf_calc_service.py`, sem qualquer consumidor de runtime ou teste.
- O módulo duplicava a valuation canônica, abria sessões próprias e podia consultar BRAPI durante cálculo financeiro.
- `fixed_income_valuation_service.py` permanece como única implementação consumida; gate estrutural protege a ausência do legado.

### Corrigido — ausência de câmbio persistido sem taxa inventada (15/08/2026)

- Resumos e snapshots deixaram de substituir ausência de USD/BRL persistido por `5.70`.
- O reader DB-first agora falha explicitamente com a data efetiva sem cobertura, preservando a busca da última taxa disponível até a data.
- Testes cobrem ausência de fallback fixo/provider e o erro de cobertura vazia.

### Removido — serviço cambial legado em tempo de request (15/08/2026)

- `fx_service.py` foi reduzido à persistência transacional usada pelo bootstrap.
- Removidas APIs órfãs de leitura que consultavam BCB/AwesomeAPI em requests e podiam retornar taxa fixa `5.70`.
- Consumidores financeiros permanecem nos readers DB-first; gate estrutural protege a fronteira sem provider e sem fallback.

### Corrigido — erros explícitos nas consultas auxiliares de ativos (15/08/2026)

- Buscas de ativos/Tesouro e preço histórico de título continuam fail-soft, mas passam a retornar erro explícito além de lista/preço vazio.
- O modal de transação consolida e exibe a falha provider-neutral, distinguindo indisponibilidade de resultado vazio.
- Falha no preço de Tesouro orienta preenchimento manual; teste estrutural cobre hooks e consumidor.

### Corrigido — erro visível na consulta de cotação (15/08/2026)

- `useTickerQuote` deixou de transformar falhas de rede/servidor em ausência silenciosa de erro.
- 404 informa ativo ausente no catálogo; demais falhas apresentam mensagem recuperável já consumida pelo modal de transação.
- Mensagem pública não expõe o provider e o catch deixou de usar `any`.

### Corrigido — conclusão recuperável do onboarding (15/08/2026)

- O `PATCH /users/me/onboarding` deixou de ter sua falha ignorada; navegação ocorre somente após persistência e atualização do usuário.
- Falhas mantêm o usuário na tela com mensagem recuperável.
- Se a carteira já tiver sido criada, o retry repete apenas a confirmação idempotente e não cria carteira duplicada.
- Adicionado teste estrutural do contrato de persistência, refresh e retry.

### Alterado — cache Redis fail-open com observabilidade (15/08/2026)

- As cinco capturas amplas da fronteira Redis deixaram de falhar silenciosamente e agora registram operação, chave/padrão sanitizado, tipo e mensagem sanitizada da exceção.
- A política fail-open foi preservada: indisponibilidade do Redis não interrompe requests nem persistência.
- Valores armazenados não são incluídos nos logs; gate AST protege ausência de `pass` e uso da sanitização.

### Alterado — invalidação de cache sem captura silenciosa duplicada (15/08/2026)

- Removidos `except Exception: pass` redundantes das invalidações de cache em atualização e exclusão de carteira.
- Os serviços agora delegam diretamente à fronteira Redis fail-open de `cache_delete`, sem alterar disponibilidade ou transações.
- Gate AST exige as duas chaves canônicas e impede nova captura silenciosa local.

### Preservado — redirects externos de Metas e IRPF (15/08/2026)

- Auditados `/metas` e `/irpf`: ambos apenas redirecionam com `replace` para as rotas canônicas sob `/carteira`.
- Os caminhos não possuem páginas, loaders, escritas ou cálculos próprios e não são usados pela navegação interna.
- Compatibilidade foi preservada para favoritos externos; teste estrutural impede que os aliases adquiram lógica funcional.

### Corrigido — hierarquia de rotas de Patrimônio (14/08/2026)

- `main.tsx` passou a importar diretamente a página consolidada canônica; removido o re-export intermediário em `pages/patrimonio/PatrimonioPage.tsx`.
- Subrotas de renda variável, Tesouro e renda fixa deixaram de ser filhas de uma página sem `<Outlet>` e passaram a ser registradas diretamente.
- `/carteira/patrimonio` preserva a visão consolidada e as três URLs específicas passam a renderizar seus componentes.
- Gate estrutural cobre o import canônico, a ausência do alias e a hierarquia corrigida.

### Removido — ação frontend para rota inexistente de Análise (14/08/2026)

- Removida do menu de posições a ação “Análise do Ativo”, que direcionava para `/carteira/analise` sem rota registrada.
- Preservadas as ações funcionais de adicionar e consultar lançamentos.
- O teste do menu passou a exigir duas ações e a ausência do link morto; o módulo de Análise continua bloqueado pela #57.

### Removido — placeholders e entradas paralelas do frontend (14/08/2026)

- Removidos placeholders órfãos de Análise/Histórico, stubs antigos de Login/Register, router alternativo e `ProtectedRoute` duplicado.
- Preservadas as entradas canônicas em `main.tsx`, `router/ProtectedRoute.tsx` e `pages/auth/*`.
- `MetasPage.tsx` não foi alterada e permanece bloqueada para o redesenho conjunto #246 + #57.
- Adicionado gate estrutural cobrindo ausência dos seis arquivos e presença das entradas válidas.

### Removido — entrada React vazia e duplicada (14/08/2026)

- Removido `frontend/src/App.tsx`, arquivo sem consumidores que continha apenas `export {}`.
- `frontend/src/main.tsx` permanece como entrada única para providers, roteamento e montagem React.
- Adicionado gate estrutural contra a restauração do placeholder ou a perda do contrato mínimo da entrada canônica.

### Removido — router administrativo de debug (14/08/2026)

- Removida a superfície `/api/v1/debug`, sem consumidores, que permitia listar usuários, redefinição de senha e criação de `superadmin` mediante segredo estático paralelo.
- Removidas a montagem condicional no `main.py` e as configurações órfãs `ADMIN_SECRET` e `DEBUG_RATE_LIMIT`.
- Gestão legítima de usuários permanece em `/api/v1/admin`, protegida por JWT e `require_superadmin`.
- Adicionado gate de segurança contra a reintrodução do arquivo, rota ou configuração.

### Removido — backfill legado de Proventos (14/08/2026)

- Removidos `backfill_dividends` e `dividend_backfill_service.py` após confirmação de que nenhum runtime, scheduler, CLI, workflow ou adapter certificado os consumia.
- Removidos testes exclusivos do fluxo antigo; as nove regras úteis de normalização foram migradas para uma suíte unitária canônica.
- Preservado o teste DB-first que impede eventos não monetários de contaminarem agregados financeiros.
- O gate estrutural agora exige a ausência física do serviço; ingestão permanece exclusiva do seed/bootstrap certificado e explicitamente habilitado.
