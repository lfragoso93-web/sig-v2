# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui. O histórico detalhado anterior permanece preservado no Git e nos changelogs datados em `docs/changelog/`.

## [Unreleased] — branch `stable-15jun`

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
