# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui. O histórico detalhado anterior permanece preservado no Git e nos changelogs datados em `docs/changelog/`.

## [Unreleased] - branch `stable-15jun`

### 17/10/2026 - contratos de Renda Fixa (#355), validacao isolada

- Adicionados metadados portfolio-scoped, GET/POST da API e associacao nullable
  em `transactions`; o ledger segue como fonte unica do lifecycle.
- Writer valida ownership e classe; FK composta no PostgreSQL impede ligacao
  entre carteiras. Sem backfill ou alteracao de registros existentes.
- Os 18 testes focados passaram; migration `20261017_fixed_income_contracts`
  aplicada na stack sintetica, com `alembic current` em `head`. Teste PostgreSQL
  transacional confirmou rejeicao cross-portfolio e rollback com contagens zero.
- Imagens de teste backend/frontend atualizadas; digests e identidade em
  `docs/USER_TEST_STACK.md`. `/health=200`; `/ready=503` esperado sem dataset e
  certificacao reais. API de contratos ainda nao foi conectada ao formulario.

### 17/10/2026 - inventario de taxonomia de Renda Fixa (#355)

- Mapeados schema, writer canonico, API, formulario, CSV, valuation e
  consumidores de snapshots/TWR; resultado em
  `docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`.
- Confirmado que metadados contratuais ainda vivem em `notes` e que a antiga
  tabela de projecao foi removida por migration irreversivel. Nenhum banco,
  schema, dado financeiro ou runtime foi alterado. Registradas proposta
  preliminar e revisao dos caminhos de escrita; a FK nullable parece compativel
  se ownership/classe forem validados e os caminhos legados forem preservados.
  A auditoria read-only em `sgi-usertest` confirmou identidade sintetica e
  encontrou zero transacoes; implementar apos preparar massa sintetica e
  validar em banco descartavel.

### 17/10/2026 - simulador de rendimentos (#359, frente A)

- Adicionada calculadora de juros compostos com aporte inicial/mensal, taxa
  efetiva anual e prazo, gráfico e evolução anual.
- A projeção é isolada: sem API, persistência, provider ou efeito na carteira.
- Premissas e limites estão em `docs/TOOLS_CALCULATORS.md`; calculadora de
  Renda Fixa permanece pendente. Typecheck, build de produção e quatro testes
  determinísticos passaram; rota e asset retornaram HTTP 200 na stack
  `sgi-usertest`. Validação visual desktop/mobile segue pendente por
  indisponibilidade do navegador integrado. Digests, SHA base e limites de
  certificação estão em `docs/USER_TEST_STACK.md`; `sig-v2` permaneceu parado.

### 17/10/2026 - stack isolada de testes assistidos

- Adicionada stack Compose `sgi-usertest`, com banco e artefatos proprios,
  frontend limitado a loopback e sem carregar o `.env` principal.
- Documentada a atualizacao da imagem a cada alteracao para testes assistidos;
  certificacao real deixa de bloquear iteracoes de desenvolvimento, enquanto
  `/ready` permanece fail-closed no runtime de dados reais.
- Imagens construidas e stack iniciada com Alembic, banco, Redis e `/health`
  saudaveis; frontend responde em loopback. `/ready` continua 503 nessa
  identidade sintetica e nao e gate da rodada assistida. O projeto `sig-v2` e
  seus volumes permaneceram intactos.

### 17/10/2026 - evidencia oficial de elegibilidade de cupons (#149)

- regulamento B3 do Tesouro Direto, item 95, define elegibilidade como título
  disponível na conta na manhã do pagamento antes de depósitos/transferências;
- itens 97–101 atribuem repasse e impostos ao Agente de Custódia, que consulta
  posições, movimentações e preços de aquisição; o CSV agregado não dá
  posição por carteira nem componente tributável universal por unidade;
- permanece necessário obter posição/custódia por conta na manhã do pagamento
  e base tributável/IRRF por lote, sem inferir do bruto;
- promoção/certificação de runtime para dados reais fica separada do trabalho
  de desenvolvimento. Fontes e limites em
  `docs/TREASURY_CASH_EVENT_SOURCE_AUDIT.md`; sem escrita ou promoção.

### 17/10/2026 - GOV-07 correlacao do backlog

- inventario GitHub consultado: 22 Issues abertas, nenhuma PR aberta; #83 ja
  consta fechada apos o ensaio HTTP administrativo;
- as Issues abertas foram agrupadas por residual concreto: #408 CodeQL, #149
  evidencias de cupons, #370 evidencia KLBN11, #272 DDL controlado, providers/
  bootstrap, backlog de produto e OCI;
- #353 ja esta implementada no `AppLayout` com testes unitarios de navegacao;
  faltam validacoes desktop/mobile previstas na Issue, portanto segue aberta
  como validacao P2, sem bloquear jornada critica;
- nao foi encontrada Issue aberta claramente duplicada ou sem destino. A ponta
  remota de `stable-15jun` nao foi confirmada: conector mostra sete commits a
  frente de `main`, mas nao retorna o SHA; `git ls-remote` falhou por rede;
- GOV-07 foi correlacionada para o snapshot local, mas #293 permanece aberta
  ate publicar/reconciliar o snapshot documental. Sem mudanca de runtime.

### 17/10/2026 - inventario estatico #272

- revisao read-only encontrou uso ativo de `event_date`, `ratio`,
  `brapi_event_id`, `raw_data`, `applied_at` e `portfolio_id` no fluxo de troca
  de ticker por carteira e/ou em fallbacks controlados do leitor;
- a contração não é uma limpeza isolada: exige primeiro migrar esse consumidor,
  preservar idempotência e então medir dados na base alvo antes de DDL;
- inventário e referências registrados em
  `docs/CORPORATE_EVENTS_LEGACY_COLUMN_INVENTORY.md`. Nenhum banco, schema,
  migration ou projeção foi alterado.

### 17/10/2026 - revisão de segurança #408

- Issue remota aberta; PRs #413/#419 e CI são citadas como concluídas;
- comentário da Issue informa deep scan CodeQL/Trivy verde em `stable-15jun`,
  mas o corpo ainda marca CodeQL pós-correção como pendente e condiciona o
  fechamento à propagação/global dos alertas;
- workflow `.github/workflows/security-deep-scan.yml` permite execução manual
  e agendada e também executa Trivy da imagem backend. A consulta disponível
  lista apenas execuções associadas a PR, sem expor execução manual/schedule
  ou alertas CodeQL. A evidência remota não pôde ser reconciliada neste bloco;
- #408 permanece aberta. Não houve nova execução do scan nem alteração runtime.


### 17/10/2026 - Issue #83 concluida

- ensaio administrativo integrado de backup, download autenticado e restore em bancos PostgreSQL descartaveis;
- autenticacao SuperAdmin, auditoria e status persistido verificados; marcador da origem permaneceu intacto e foi restaurado no alvo vazio;
- roteiro e limites operacionais registrados em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md`; Issue #83 fechada no GitHub;
- nenhum banco ou volume operacional foi usado; #408 e GOV-07/#293 permanecem como proximos gates separados.

### 17/10/2026 - recuperacao dos gates backend

- a persistencia estrita rejeita colecoes com linhas BRAPI e Yahoo simultaneas, reforcando a regra de fallback explicito; fixtures de eventos corporativos foram alinhadas a prioridade B3 para ativos listados;
- scanners AST passaram a tolerar BOM UTF-8; o adapter B3 teve anotacoes locais ajustadas para mypy e `goals_service.py` recebeu o espacamento exigido pelo flake8;
- backend: 2.401 testes passaram e 5 foram skipped; flake8, mypy (411 arquivos), Architecture Doctor (6/6), migrations frescas em PostgreSQL 16 e drift gate passaram;
- o entrypoint agora aplica o head runtime seguro `20261016_corp_ev_effective_date`; testes focados do alvo/migration passaram (10/10);
- imagens backend e frontend do candidato foram construidas e implantadas; backend, PostgreSQL e Redis estao saudaveis, readiness assistida retornou `GO_ASSISTED` e `/ready` segue 503 por divergencia do evento anterior;
- backup v3 pos-migration teve zero escritas na origem; restore isolado reconciliou sem divergencias; proof e dry-run #384 foram gerados sem promover a identidade.

### 16/10/2026 - rebaseline documental e runtime observado

- correção da baseline: `stable-15jun` está em
  `b37661921e3a8455f45c8b676b28955d6ad3d0ea`, 7 commits à frente e 0 atrás de
  `main` (`4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`); não havia PR aberta;
- inventário GitHub: 453 Issues, 23 abertas, 430 fechadas;
- antes desta rebaseline, o working tree continha 15 arquivos modificados e
  cinco itens não rastreados; esta entrada registra o estado sem incluir os
  artefatos no candidato;
- runtime observado: `/health=200`; `/ready=503` por `runtime_identity_error`,
  com `ready_for_real_data=false`; APP SHA diverge do checkout e dataset está
  sem referência;
- a CLI de readiness assistida não concluiu e não produziu relatório;
- `docs/DEVELOPMENT_BASELINE_2026-10-16.md` passa a concentrar a fotografia e o
  mapa. A promoção de 06/10 permanece histórica e não certifica o runtime atual.

### 16/10/2026 - B3 como fonte prioritária para proventos e eventos

- alinhada a política local para usar B3 como autoridade de ativos listados,
  com BRAPI complementar e Yahoo como fallback explícito;
- adapter Listed Companies cobre proventos e eventos B3 para ações/BDRs;
- `effective_date` passa a aceitar nulo para eventos sem sessão efetiva
  comprovada; `lastDatePrior` permanece evidência de direito, não data efetiva;
- a lacuna NIKE34 fica delimitada a carga de dividendos B3 por ativo e análise
  fail-closed do grupamento/fração antes de qualquer projeção.

### Histórico 16/10/2026 - rebaseline de segurança, backup administrativo e continuidade

- PR #425 sincronizou `main` com `stable-15jun`; a árvore comum naquele momento
  estava no SHA `8e4e243416014024964031793dbb7b15bcd3c39d`;
- PR #413 integrou a sanitização dos logs e #419 acrescentou regressões; CI
  passou, mas a confirmação CodeQL pós-correção permanece pendente;
- PR #418 completou o hardening administrativo da #83: reautenticação,
  AuditLog, status persistido, download autenticado e retenção configurável;
- PR #412 publicou a resolução explícita de frações pendentes de eventos
  corporativos; caixa só é projetado quando a evidência de liquidação está
  presente, mantendo a #370 fail-closed para KLBN11;
- Issues #408, #83 e #293 foram rebaselined com os resíduos e gates atuais;
- README, ROADMAP, arquitetura, readiness, continuidade, governança e status
  de eventos corporativos foram atualizados;
- a identidade certificada em 06/10/2026 continua histórica. O estado posterior
  do runtime está registrado na entrada mais recente deste changelog e no mapa
  de baseline.

### 11/10/2026 - #149 auditoria oficial de cupons do Tesouro

- o dataset oficial `resgates-do-tesouro-direto` foi identificado como fonte
  factual de título, vencimento, pagamento e valor bruto unitário de cupons;
- uma CLI estritamente read-only passou a validar schema, consistência agregada
  e capacidade factual sob `treasury-cash-event-source-audit.v1`;
- ausência de `record_date`, elegibilidade por carteira e componente tributável
  mantém todos os eventos não promovíveis e `database_writes_executed=0`;
- nenhum seed, migration, rebuild ou acesso ao banco foi introduzido.

### 11/10/2026 - #149 contratos de TWR dedicados consolidados

- Renda Fixa passou a ter oracles explícitos para aportes, resgates parciais,
  múltiplas aplicações, composição temporal e fronteiras de benchmark;
- Tesouro passou a consumir cupons e amortizações canônicos uma única vez no
  TWR, preservando PU e calendário ausentes como estados fail-closed;
- README, ROADMAP, arquitetura e mapa de dados canônicos foram alinhados ao
  código comprovado;
- a #149 permanece aberta apenas para evidência factual de elegibilidade de
  cupons/amortizações e para a certificação operacional de uma nova identidade;
- este bloco não executa seed, rebuild, escrita financeira nem promoção de
  certificação.

### 06/10/2026 - #344 Architecture Enforcement concluída

- #345–#350 foram fechadas após implementação e validação dos seis blocos da
  Epic;
- o Architecture Doctor cataloga SGI001–SGI015 e preserva os gates originais;
- Agent Skills versionadas, Certification Proof, runtime determinístico,
  Access Context e lease distribuído do scheduler foram integrados;
- a avaliação de Reliable Async documentou a decisão de não introduzir
  transactional outbox sem uma escrita de domínio e trabalho durável que
  precisem compartilhar a mesma transação;
- os macroblocos foram promovidos para `main` pelas PRs #385 e #393–#396.

### 06/10/2026 - #384 certificação persistente guardada

- as PRs #386 e #387 promoveram o modelo append-only, migration, leitor
  DB-first, relatório, contrato de evidência, executor transacional e CLI;
- a CLI permanece dry-run por padrão e exige `--execute` mais confirmação forte
  para gravar um único evento auditável;
- a promoção operacional real foi executada para a identidade runtime no SHA
  `3ab054f61e34f440dddf93c170259958243d58af`, com evento `PROMOTE` append-only;
- o reader DB-first validou cadeia, hash, evidência e identidade completa;
  `ready_for_real_data=true` e `/ready=200` persistiram após restart;
- mudanças futuras de SHA, dataset ou revision Alembic exigem novo ciclo de
  evidência e certificação e falham fechado até nova promoção válida;
- uma suíte opt-in, restrita a banco explicitamente de teste, comprovou advisory
  lock, idempotência concorrente, stale-plan e restart em PostgreSQL 16 efêmero;
- `/ready` passou a resolver a identidade runtime independentemente, validar a
  revision Alembic viva e consumir a certificação persistida; configuração
  ausente, mismatch, revogação ou erro de leitura permanecem em 503;
- a documentação operacional foi rebaselizada e ganhou um runbook canônico para
  impedir comandos e critérios divergentes.

### 23/09/2026 - rebaseline documental pós-#370

- README, ROADMAP e DEVELOPMENT_CONTINUITY foram alinhados ao estado mais novo
  registrado no checklist da #158;
- a documentação raiz deixa de afirmar que eventos corporativos materiais ainda
  permanecem `UNRECONCILED`;
- estado vigente: AMOB3 formalizada como `MATCHED`/`CONFLICT`, KLBN11 em
  `CONFLICT` revisável, e zero eventos corporativos materiais com posição
  aberta em `UNRECONCILED`;
- KLBN11 continua bloqueada para eventual `MATCHED` até haver evidência
  documental de liquidação fracionária; `ready_for_real_data=false` permanece.

### 23/09/2026 - #158 checkpoint operacional de runtime

- checklist da #158 registrou o SHA `b39edd8f86e7f94b95ea5a45585480cca092cdb2`
  com gates locais sem escrita aprovados: 137 testes focados, `compileall`,
  `mypy app --check-untyped-defs` e `git diff --check`;
- congelamento final da #158 segue bloqueado por runtime Docker/Postgres:
  `localhost:5432` indisponível, Docker/Docker Compose sem resposta dentro do
  timeout operacional, `com.docker.service` parado e WSL com `E_ACCESSDENIED`;
- não houve seed, rebuild, migration, `--execute`, escrita em banco, alteração
  de ledger ou promoção de `ready_for_real_data`;
- retomada permitida quando o runtime voltar: `docker compose ps`,
  `user_test_readiness` no backend e validação de reconciliacao runtime,
  restart, persistência e idempotência no mesmo SHA candidato.

### 23/09/2026 - #158 runtime Docker/Postgres validado

- no SHA `7b5b5838dcab3d50145152fc72955e697b9d2f94`, Docker/Postgres estavam
  ativos; o bloqueio era permissão do usuário corrente no pipe
  `dockerDesktopLinuxEngine`, contornado por execução elevada sem remover
  volumes, containers ou dados;
- `docker compose ps` mostrou `backend`, `db`, `redis`, `frontend` e
  `cloudflared` ativos, com `backend`, `db` e `redis` saudáveis;
- `user_test_readiness` retornou `GO_ASSISTED`, `blockers=[]`, `warnings=[]`,
  `writes_executed=0`, `ready_for_real_data=false`, com 8 usuários,
  7 carteiras, 423 transações, 3677 ativos, 4409462 preços, 978 snapshots,
  431 Proventos, 123 eventos corporativos e 2 metas;
- inventário `pre-prod-inventory.v2` retornou 21 tabelas, 4437703 linhas,
  0 tabelas não classificadas e 0 findings bloqueantes;
- `/health=200` com Postgres/Redis `ok`; `/ready=503` permanece esperado;
- AMOB3 está formalizada como `CONFLICT`/`MATCHED`, KLBN11 2025 como
  `CONFLICT`, e a consulta de eventos `UNRECONCILED` com posição positiva na
  data do evento retornou 0 linhas;
- restart controlado de `backend` e, depois, de `db` + `backend` preservou
  health, readiness e contagens, validando persistência/idempotência runtime
  sem seed, rebuild, migration, `--execute`, alteração de ledger ou promoção
  de dados reais amplos.

### 23/09/2026 - #269 CERT-01B iniciado

- gate local de segurança iniciado sobre o SHA
  `e5bc987b92335eb943e5cf1aeda9008ffc051f13`;
- Gitleaks encontrou um falso positivo documental em
  `docs/changelog/2026-09-15-promotion-reconciliation-158-corporate-event-decision.md`,
  causado por texto técnico `BRAPI: label=GRUPAMENTO`;
- `.gitleaks.toml` recebeu allowlist cirúrgica para esse trecho específico e a
  reexecução do Gitleaks varreu 4036 commits com `no leaks found`;
- Hadolint passou para `backend/Dockerfile` e `frontend/Dockerfile`;
- imagens runtime backend/frontend foram buildadas no SHA candidato;
- identidades runtime confirmadas como não-root: backend UID 1000 e frontend
  UID 101;
- smoke HTTP do frontend runtime serviu `/` com sucesso e o container
  temporário foi removido;
- Trivy filesystem foi concluído em worktree limpo do SHA publicado, sem
  artefatos locais não rastreados como `.env`, `.agents`, `.tmp` e cache do
  scanner: 0 vulnerabilidades HIGH/CRITICAL, 0 secrets e 0 misconfigs nos
  alvos detectados;
- Trivy runtime image passou para frontend Alpine 3.24.1 com 0
  vulnerabilidades HIGH/CRITICAL;
- Trivy runtime image passou para backend Debian 13.7 e pacotes Python com 0
  vulnerabilidades HIGH/CRITICAL.

### 23/09/2026 - #269 inventario externo GitHub

- Code Scanning aberto no GitHub: 0 alertas;
- Secret Scanning aberto no GitHub: 0 alertas, sem impressao de valores de
  segredo;
- Dependabot aberto no GitHub: 2 alertas `medium`, ambos em dev dependencies do
  frontend no default branch: `vitest` e `@vitest/mocker`, advisory
  `GHSA-82fw-gwwq-j7x9` / `CVE-2026-84373`, corrigido em 4.1.11;
- o SHA candidato em `stable-15jun` ja usa `vitest` 4.1.11,
  `@vitest/mocker` 4.1.11 e `@vitest/coverage-v8` 4.1.11 no
  `frontend/package-lock.json`;
- `npm audit --omit=dev --audit-level=moderate`: `found 0 vulnerabilities`;
- `npm audit --audit-level=moderate`: `found 0 vulnerabilities`;
- conclusao: alertas Dependabot pertencem ao default branch ainda defasado, nao
  ao SHA candidato de `stable-15jun`; a baixa efetiva deve ocorrer quando o
  macrobloco certificado for promovido para `main` ou quando `main` receber
  backport dedicado da atualizacao Vitest.

### 23/09/2026 - rebaseline documental para #284

- README, ROADMAP e DEVELOPMENT_CONTINUITY foram alinhados ao estado em que
  #158 e #269 possuem evidencia local publicada no SHA candidato;
- o proximo bloco operacional passa a ser homologacao OCI (#284) sobre o mesmo
  SHA candidato;
- `ready_for_real_data=false` permanece obrigatorio ate decisao GO/NO-GO da
  #227.

### 23/09/2026 - #284 preflight local e pacote exact-SHA

- `scripts/oci_compose_preflight.ps1` foi alinhado ao contrato real do backend:
  workers sao controlados por `BACKEND_WORKERS=1` no ambiente e consumidos pelo
  `entrypoint.sh`;
- `scripts/oci_local_readiness.ps1` passou em `stable-15jun` com arvore
  rastreada limpa, sem artefatos sensiveis rastreados, Compose OCI sem portas
  publicadas para backend/frontend e `cloudflared` presente;
- pacote de fonte OCI gerado via `git archive`; o manifesto local registra SHA,
  SHA-256 e contagem de arquivos rastreados para o operador validar antes da
  transferencia;
- pacote/manifesto permanecem em `artifacts/oci-source-package/`, ignorados por
  Git, para transferencia operacional controlada; `ready_for_real_data=false`
  nao foi alterado.

### 15/09/2026 - #158 eventos corporativos materiais decididos

- os 15 eventos corporativos inicialmente materiais foram cruzados com a
  exposicao real da carteira 15 na data de cada evento;
- todos continuam `UNRECONCILED/requires_review=true` e, pelo contrato
  fail-closed atual, nao entram nas projecoes financeiras;
- 4 eventos possuem quantidade positiva no evento e bloqueiam o GO ate
  reconciliacao ou descarte formal: `AMOB3` bonificacao/grupamento e `KLBN11`
  bonificacao/desdobramento;
- os demais 11 eventos ocorreram sem posicao na data; `POMO4` possui posicao
  final aberta, mas seus eventos de 2025 ocorreram antes das recompras de 2026;
- simulacao read-only pelo motor puro mostrou que aplicar mecanicamente os 4
  eventos pendentes mudaria realizado e deixaria residuo de posicao em
  `KLBN11`, logo #370 exige reconciliacao economica antes de rebuild;
- normalizador BRAPI passou a respeitar labels explicitos `GRUPAMENTO` e
  `DESDOBRAMENTO` em `stockDividends`, prevenindo nova classificacao semantica
  errada como bonificacao;
- simulacao por fonte isolada concluiu que nenhum dos 4 eventos de
  `AMOB3`/`KLBN11` pode ser marcado como `MATCHED` no dataset candidato sem
  reconciliacao adicional de extrato/fracao/residuo;
- decisao arquitetural: eventos corporativos materiais fazem parte do lifecycle
  do investidor e #370 permanece blocker da #158 ate associacao/reconciliacao
  no banco ou politica canonica de conflito/fração/residuo;
- contrato puro de reconciliacao criado para planejar `CONFLICT` e `MATCHED`
  sem escrever no banco, sem rebuild e sem colocar eventos revisaveis na
  projecao financeira;
- CLI read-only de dry-run emite planos auditaveis para `AMOB3` e `KLBN11`
  com `database_writes_executed=0` e `dry_run=true`, preparando persistencia
  controlada posterior de `CONFLICT`;
- executor controlado persistiu `CONFLICT` para os quatro eventos materiais no
  banco restaurado isolado, mantendo `requires_review=true`,
  `is_canonical=false` e os eventos fora da projecao financeira;
- contrato de evidencia para futuro `MATCHED` agora exige referencia de
  extrato/corretora e politica explicita de fracao/residuo; `MANUAL_REVIEW`
  nao autoriza evento reconciliado;
- foi criada a Issue #370 e a #158 permanece bloqueada para #269/#284/#227,
  PR estrutural para `main` e `ready_for_real_data=true`.

### 14/09/2026 — A1/#352 validada e fechada

- #352 foi corrigida e validada manualmente: o seletor de `Tipo de ativo`
  substitui a barra de classes no modal de lancamento;
- a transacao foi adicionada com sucesso no fluxo atualizado;
- #352 deixou de ser candidato P1 aberto e passa a ser evidencia consumida por
  #303;
- #354 permanece fechada enquanto a politica de senha frontend/backend seguir
  alinhada;
- `PORTFOLIO-TEST-READY` foi consolidado em #303 no SHA publicado, sem alterar
  `ready_for_real_data=false`;
- #226 e #216 foram posteriormente consumidas; o gate corrente da Trilha A é
  #158.

### 14/09/2026 — #226 Proventos decidido

- a evidência portfolio-scoped/idempotente de Proventos foi aceita como
  suficiente para o escopo de promoção controlada;
- não haverá seed global mecânico apenas por checklist histórico;
- eventual global controlado fica condicionado a necessidade material nova em
  #216/#158;
- `asset_dividends` permanece a única persistência canônica global e direitos de
  carteira continuam calculados sob demanda.

### 14/09/2026 — #216 gate agregado fechado

- benchmarks e câmbio permanecem como evidências consolidadas;
- a decisão de #226 foi consumida como componente material restante de
  Proventos;
- não haverá seed global de Proventos por repetição de checklist histórico;
- #158 passa a ser o próximo gate da Trilha A;
- PR `stable-15jun` -> `main` continua bloqueada até #158, #269, #284 e #227.

### 14/09/2026 — #158 rebaseline operacional iniciado

- #158 passa a consumir #303, #226 e #216 como evidências fechadas;
- promotion reconciliation deve executar somente o delta necessário sobre
  SHA/dataset congelados;
- seeds globais, rebuilds amplos, importações e contrações físicas continuam
  proibidos sem gate explícito dentro da própria #158;
- checklist executável publicado em
  `docs/promotion-reconciliation-158-checklist.md`;
- o próximo avanço deve produzir evidência operacional antes de #269, #284 e
  #227.

### 14/09/2026 — #158 validação local read-only preparada

- banco Docker local estava sem tabelas públicas; foi migrado em base vazia até
  `20260910_goals_runtime`, alvo runtime-safe do entrypoint;
- a cadeia Alembic aplicada inclui `20260731_drop_legacy_divs`; neste ambiente
  não havia dados/tabelas prévias, portanto não houve perda de dataset;
- inventário `pre-prod-inventory.v2` passou com 20 tabelas, 0 unclassified e 0
  blocking findings;
- `user-test-readiness.v1` retornou `NO_GO` por ausência de usuários,
  carteiras, transações, ativos, preços, snapshots, Proventos e eventos;
- nenhuma importação, seed, rebuild, provider ou promoção de
  `ready_for_real_data=true` foi executada.

### 14/09/2026 — #158 dataset candidato bloqueado

- busca local em `artifacts/` e em `C:\Users\Acer\Documents\Codex` não encontrou
  `pre-prod-backup.v3`, `backup-report.json`, `database.dump` ou
  `origin-inventory.json`;
- checklist da #158 passou a exigir caminho local do artefato de backup aprovado
  ou justificativa explícita para dataset sintético/controlado antes de qualquer
  import/rebuild;
- banco apenas migrado com schema e sem usuários/carteiras/transações permanece
  NO-GO para reconciliation operacional.

### 14/09/2026 — #158 artefato candidato bloqueado por identidade runtime

- artefato `pre-prod-backup.v3` gerado para o SHA
  `1e7c3fca6e6acaea19a75c1197f036a1f1021199` em
  `C:\Users\Acer\Documents\Codex\sgi-v2-backups\20260914-233314`;
- backup com snapshot consistente, `pg_dump`/PostgreSQL major 16/16,
  `database.dump` de 40.977.216 bytes e SHA-256
  `486d971f25e7924249fac2c8b2630e59b746e16aeaa93bc5dc963093d9e33b81`;
- inventário de origem registrou 20 tabelas, 4.434.193 linhas, 0 tabelas sem
  classificação e 0 findings bloqueantes;
- `scripts\oci_backup_artifact_check.ps1` aprovou presença dos arquivos
  obrigatórios, JSONs, conteúdo do dump e checksum;
- verificação posterior encontrou runtime `APP_COMMIT_SHA=unknown` no container
  de origem e checkout local divergente do SHA informado;
- o artefato fica bloqueado para restore candidato e deve ser regenerado em
  runtime com `APP_COMMIT_SHA` igual ao SHA certificado;
- a CLI `pre_prod_backup` passou a falhar quando `APP_COMMIT_SHA` estiver
  ausente/`unknown` ou divergir do `--commit-sha` informado;
- restore, import, rebuild, cleanup, migration destrutiva e
  `ready_for_real_data=true` continuam bloqueados.

### 14/09/2026 — #158 backup candidato regenerado com SHA runtime

- imagem backend temporaria `sig-v2-backup:48b5041c` foi construida a partir do
  SHA `48b5041ceaf3240384065c42578fde6689ce17db`;
- novo `pre-prod-backup.v3` foi gerado contra o Postgres local de origem sem
  alterar o checkout operacional sujo em `E:\Sistema Investimentos\App\SGFP\sig-v2`;
- artefato local:
  `artifacts\pre-prod-rebuild\20260915-002119`;
- backup com snapshot consistente, `pg_dump`/PostgreSQL major 16/16,
  `database.dump` de 40.981.404 bytes e SHA-256
  `d42efc2f507854b58ab30429530aee10462c3b41ad29467db57ab91dfe77b4c9`;
- inventario de origem registrou 20 tabelas, 4.434.818 linhas, 0 tabelas sem
  classificacao e 0 findings bloqueantes;
- `scripts\oci_backup_artifact_check.ps1` aprovou presenca dos arquivos
  obrigatorios, JSONs, conteudo do dump e checksum;
- proximo passo permitido: restore isolado/descartavel para reconciliation;
  import, rebuild, cleanup, migration destrutiva e `ready_for_real_data=true`
  continuam bloqueados.

### 14/09/2026 — #158 restore isolado reconciliado

- artefato `20260915-002119` restaurado em banco descartavel
  `sgi_restore_20260915_002119`;
- `restore-report.json` retornou `pre-prod-restore.v1` com `ok=true`;
- `reconciliation-report.json` retornou `pre-prod-reconciliation.v1` com
  `ok=true`;
- migrations de origem e destino coincidiram:
  `20260906_rate_source32`, `20260910_goals_runtime`;
- nao houve tabelas ausentes, tabelas inesperadas, divergencias de
  classificacao, divergencias de contagem ou divergencias de findings;
- seguranca preservada: zero escritas na origem, restore somente no alvo,
  sem cleanup e sem rebuild;
- proximo passo permitido: iniciar as validacoes read-only da reconciliation
  sobre o dataset restaurado; import/rebuild/cleanup real e
  `ready_for_real_data=true` continuam bloqueados.

### 14/09/2026 — #158 validação read-only do dataset restaurado

- `pre-prod-inventory.v2` passou sobre `sgi_restore_20260915_002119` com
  20 tabelas, 4.434.818 linhas, 0 tabelas sem classificacao e 0 findings
  bloqueantes;
- `user-test-readiness.v1` retornou `GO_ASSISTED`, sem blockers/warnings e com
  `ready_for_real_data=false`;
- dataset restaurado contem 6 carteiras, 7 usuarios, 366 transacoes, 608
  snapshots consolidados, 5.121 snapshots por classe, 184 eventos globais de
  Proventos e 123 eventos corporativos;
- eventos corporativos seguem como delta material: 122 `PENDENTE/UNRECONCILED`
  e 1 `APLICADO/UNRECONCILED`, todos `requires_review=true`;
- snapshots preservam explicitamente dias com cobertura parcial/preco estimado,
  sem mascarar ausencia como zero;
- evidencia Tesouro lida em `transactions` mostrou pares legado/canonico com
  quantidades liquidas opostas/complementares; o achado foi registrado na #365
  sem iniciar Trilha B;
- nao ha tabelas fisicas `irpf*`; IRPF deve continuar validado por servicos
  runtime suportados, sem recriar legado;
- proximo passo permitido: reconciliation read-only focada nos deltas materiais
  antes de qualquer import/rebuild/cleanup.

### 15/09/2026 — #158 reconciliation read-only focada

- eventos corporativos materiais foram reduzidos de 123 pendencias brutas para
  15 eventos a decidir no escopo da carteira 15;
- 14 eventos globais pendentes caem dentro da janela de exposicao da carteira
  15 e 1 `TICKER_CHANGE` de `PETZ3` ja aplicado permanece
  `UNRECONCILED/requires_review=true`;
- os 15 eventos materiais envolvem `AMOB3`, `FIQE3`, `GOAU4`, `ITSA4`,
  `KLBN11`, `KLBN4`, `PETZ3` e `POMO4`;
- `POMO4` e o unico ticker material com posicao liquida aberta observada
  (30 unidades); os demais estao zerados no ledger, mas ainda podem afetar
  historico, custo, snapshots e IRPF;
- auditoria Tesouro read-only retornou 152 ativos, 151 grupos canonicos, 0
  duplicidades, 0 candidatos de migracao e `destructive_changes=false`;
- IRPF runtime da carteira 15 emitiu `irpf-annual-assessment.v1` para 2025 e
  2026 sem tabelas fisicas legadas;
- nenhum import, rebuild, cleanup real, migration destrutiva, seed global ou
  promocao de `ready_for_real_data=true` foi executado.

### 12/09/2026 — recuperação local de gates e contrato canônico de Proventos

- a recuperação da #363 passou a usar suíte local completa como ferramenta de descoberta; a PR estrutural #362 permanece fechada/draft durante o saneamento para evitar consumo iterativo de GitHub Actions;
- contratos de snapshot foram alinhados ao writer único `portfolio_snapshot_canonical_twr_service.py`, mantendo `portfolio_snapshot_service.py` restrito à invalidação;
- o contrato vigente de Proventos foi explicitado como `pre-prod-dividends-seed.v2`;
- `asset_dividends` permanece a única persistência canônica de eventos globais de Proventos;
- direitos de carteira são calculados sob demanda a partir das posições históricas, sem materialização por carteira;
- README, ROADMAP e CHANGELOG foram sincronizados para refletir essa fronteira canônica.

### 10/09/2026 — rebaseline de governança e certificação

- `user-test-readiness.v1` consolidado como gate read-only para validação assistida;
- estado registrado: `GO_ASSISTED`, `ready_for_real_data=false`, `/health=200`, `/ready=503`;
- #303 rebaselined para governar o fechamento de `PORTFOLIO-TEST-READY` e o SHA candidato;
- #226, #216, #158 e #227 rebaselined para consumir evidências já certificadas, evitando repetição destrutiva por checklist histórico;
- cadeia de promoção formalizada como #303 → #226 → #216 → #158 → homologação OCI → #227;
- OCI redefinida como ambiente de homologação do SHA exato certificado localmente, não ambiente de desenvolvimento;
- deploy OCI deve confirmar `APP_COMMIT_SHA == git rev-parse HEAD`;
- `/ready=503` permanece comportamento esperado enquanto `ready_for_real_data=false`;
- #58 reclassificada como parcialmente implementada após validação do detalhe de ativo;
- #149 reclassificada como dívida financeira parcial, não blocker automático quando a ausência de TWR é explícita;
- #246 atualizada para reconhecer Metas operacionalmente funcional após migration runtime-safe, preservando o macroprojeto definitivo como futuro;
- #351 classificada como epic pós-GO;
- #352 identificada como candidato P1 se ainda reproduzível;
- #354 foi fechada após alinhamento da política de senha frontend/backend;
- #353 classificada como P2 por padrão;
- #355–#361 classificados como evolução pós-GO, com #360 precedendo #361;
- README, ROADMAP e CHANGELOG rebaselined para remover baselines históricos tratados como instruções vigentes.

### Evidências funcionais acumuladas

- backend completo anteriormente certificado com `1880 passed, 1 skipped, 10 warnings` no ciclo #303;
- frontend anteriormente certificado com `npm ci`, typecheck, lint, Vitest e build;
- CSV sintético/assistido com dry-run, import, replay, atomicidade e rebuild canônico;
- carteira assistida com 308 transações e 65 ativos distintos;
- rebuild histórico observado com 493 snapshots entre 22/10/2024 e 10/09/2026;
- Proventos portfolio-scoped idempotentes com 49 ativos elegíveis e 183 eventos na janela validada;
- Tesouro DB-first, Renda Fixa dedicada e IRPF para classes suportadas exercitados em runtime;
- eventos corporativos portfolio-scoped disponíveis; no dataset alvo, a varredura
  mais recente registrou zero eventos materiais em `UNRECONCILED`, com KLBN11
  preservada em `CONFLICT` revisável.

### Arquitetura preservada

- `transactions` é a fonte canônica do lifecycle;
- runtime financeiro é DB-first;
- providers ficam fora do read path financeiro;
- `summary.v2`, `rentabilidade.v2`, snapshots e projetores compartilhados continuam contratos canônicos;
- Proventos pertencem ao ativo em `asset_dividends`;
- eventos corporativos pertencem ao ativo em `corporate_events`;
- ausência/cobertura parcial permanecem explícitas e não viram zero/fallback silencioso.

### Pendências para o primeiro GO

1. executar o delta final #158;
2. executar #269 no mesmo SHA candidato;
3. homologar exatamente o mesmo SHA na OCI (#284);
4. #227 emitir GO/NO-GO;
5. somente após GO avaliar `ready_for_real_data=true` e promoção para `main`.

## Histórico

O detalhamento de sanitização arquitetural, segurança, BRAPI/COTAHIST, Proventos, TWR, dependências, OCI e demais microblocos anteriores a este rebaseline permanece disponível no histórico Git e nos documentos datados. A partir deste ponto, este arquivo prioriza marcos de release e governança para evitar que microcommits históricos sejam interpretados como estado operacional atual.


## 2026-10-17 — Issue #355: integracao do contrato de Renda Fixa

O formulario de transacoes agora cria e associa o contrato estruturado no mesmo fluxo transacional da aplicacao/resgate; edicao mantem o vinculo e os valores contabeis originais. A selecao de contratos existentes e o caminho legado sem contrato continuam disponiveis. CSV antigo permanece aceito sem inferir vinculo nem criar contratos automaticamente. Testes focados do frontend (16), typecheck e quatro testes backend do fluxo/API/CSV passaram. A atualizacao da imagem de testes e os limites de prontidao estao registrados em `docs/USER_TEST_STACK.md`.


## 2026-10-18 - Issue #355: CSV com contratos estruturados

O modelo CSV agora inclui campos opcionais de contrato de Renda Fixa e a chave `fixed_income_contract_key` para agrupar varias transacoes no mesmo contrato. O dry-run valida taxonomia, datas, taxa e consistencia entre linhas; a importacao cria um contrato por chave no mesmo lote atomico. Nova exportacao autenticada por carteira permite round-trip sem transportar IDs internos. O formato antigo de nove colunas continua aceito. Validacao: 82 testes backend focados, 7 testes do modal, typecheck e Flake8 sem erros fora dos avisos legados de comprimento/linhas em branco. Runtime e digests em `docs/USER_TEST_STACK.md`.

## 2026-10-18 - Contratos transparentes e prefill por instrumento

Contrato equivalente agora e reutilizado automaticamente dentro da mesma
carteira quando todos os termos tipados e o nome coincidem; o formulario nao
expoe IDs/seletor de contrato na criacao normal. Atalhos do resumo preenchem os
termos quando existe correspondencia unica. O atalho de Tesouro preenche
vencimento conhecido e continua resolvendo indexador/taxa/PU via catalogo e
cotacao persistida. Sem migracao ou alteracao do ledger.

Imagem implementada na stack `sgi-usertest` apos recuperacao automatica do
Docker; runtime e limites registrados em `docs/USER_TEST_STACK.md`.

Validacao subsequente: 12 testes backend do servico passaram; typecheck passou.
Teste frontend foi iniciado, mas o Vitest ficou sem progresso e foi encerrado,
sem resultado. A imagem foi reconstruida e aplicada; browser integrado nao
estava disponivel para checagem visual.

## 2026-10-18 - Isolamento do agrupamento de contratos RF

Adicionada regressao confirmando que contratos com termos e nome equivalentes
continuam separados entre carteiras. Os 13 testes focados do servico passaram
em SQLite em memoria. O runtime de testes foi atualizado; digests e escopo em
`docs/USER_TEST_STACK.md`. A valida��o visual segue pendente de navegador.

A imagem backend apos o teste de isolamento por carteira esta ativa e saudavel
(`sha256:700171073da7ac0fff016e3f64627f19dc0a72ff0aaf6ea90667c63d367e7708`).
Base de teste permaneceu vazia; `/health=200`, `/ready=503` e frontend 200.

A normalizacao de identidade dos contratos RF foi ajustada: espacos repetidos
sao colapsados nos campos display_name/issuer e a comparacao do emissor ignora
caixa. A regressao focada dos 13 testes passou; imagem e runtime atualizados
conforme `docs/USER_TEST_STACK.md`.

Digest final backend para o bloco de normalizacao:
`sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58`.

A governanca local da #355 foi alinhada ao estado corrente e identifica que o
criterio remoto de seletor explicito ainda precisa ser atualizado. Nenhuma
atualizacao foi publicada no GitHub neste bloco.

## 2026-10-18 - Stack completa atualizada para testes assistidos

Frontend e backend atuais foram aplicados em `sgi-usertest`. A interface e o
bundle respondem HTTP 200; OpenAPI expoe contratos RF e exportacao CSV. DB,
Redis e volumes preservados; ledger e contratos vazios. `/ready=503` e esperado
para identidade sintetica e nao indica certificacao real. Vitest de prefill e
revisao visual integrada continuam pendentes; detalhes e digests em
`docs/USER_TEST_STACK.md`.
