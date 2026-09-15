# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui. O histórico detalhado anterior permanece preservado no Git e nos changelogs datados em `docs/changelog/`.

## [Unreleased] — branch `stable-15jun`

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
- eventos corporativos portfolio-scoped disponíveis, com reconciliação material ainda pendente para casos complexos.

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
