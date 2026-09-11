# GOV-07 — Auditoria de divergência `stable-15jun` → `main`

Data: 2026-09-11

## Objetivo

Registrar o delta acumulado de promoção exposto pela PR draft #362 antes de qualquer tentativa de merge para `main`, separando evolução canônica, gates de certificação, migrations, documentação, frontend e dívida residual.

Este documento é diagnóstico de governança. Não autoriza merge, não altera readiness e não substitui a certificação local do SHA candidato.

## Baseline da auditoria

- branch de desenvolvimento: `stable-15jun`;
- base da PR #362: `main` em `cd69044322fd3c6f48545cad5e7df047cffdafd5`;
- head no início da auditoria: `8c9580613b485475211982cc459c44a911fe40be`;
- head após correções imediatas do snapshot cycle: `a7dfa09e7ca61ca52a154a6c0421b2cf77bc820c`;
- PR #362: draft;
- delta observado na abertura: 298 commits, 228 arquivos, +13.848/-6.624 linhas;
- GitHub recalculou a PR como `mergeable=true`; o `mergeable=false` imediatamente após a abertura foi estado transitório enquanto o merge test era calculado.

O tamanho da PR reflete a promoção acumulada da `stable-15jun`, não apenas o GOV-07. Tamanho elevado não é, isoladamente, finding de arquitetura, mas exige promoção por gates e reconciliação explícita.

## Classificação dos 228 arquivos alterados

### 1. Arquitetura e núcleo financeiro canônico — preservar

O delta contém a consolidação DB-first e contratos financeiros que já sustentam a certificação atual, incluindo:

- valuation canônico de carteira;
- lifecycle/position state;
- preços persistidos e cobertura;
- Tesouro Direto;
- Renda Fixa;
- snapshots/TWR;
- Proventos asset-based;
- IRPF;
- transações e CSV;
- summary/positions.

A promoção não deve tentar reduzir o diff revertendo essas fronteiras para contratos antigos da `main`.

### 2. Certificação, readiness e CLIs — preservar, porém recuperar quality gate

Existe expansão material em `backend/app/certification`, CLIs de certificação, fixtures e testes de reconciliação.

Esses arquivos são parte do processo que produziu `GO_ASSISTED`; não são feature de usuário e não devem ser confundidos com código morto apenas por serem utilitários de certificação.

O gate de typing atualmente impede considerá-los prontos para promoção. A dívida foi registrada na Issue #363.

### 3. Migrations — gate obrigatório de promoção

A PR inclui três migrations posteriores à base da `main`:

- `20260906_rate_history_coverages.py`;
- `20260906_rate_history_source32.py`;
- `20260910_goals_runtime_contract.py`.

Antes de promoção, o SHA candidato deve passar o fresh database migration gate e a reconciliação prevista em #158. A presença das migrations no diff não autoriza execução destrutiva em ambiente com dados reais.

### 4. Documentação e operação — sincronizar no GOV-07H

A PR traz README/ROADMAP/CHANGELOG, runbooks de certificação, bootstrap, OCI e operações, além da remoção da documentação histórica da raiz.

A documentação canônica deve ser sincronizada novamente somente após os blocos de limpeza e o SHA candidato estabilizarem. Não há motivo para restaurar os documentos históricos removidos no GOV-07A.

### 5. Frontend — exigir validação assistida P0/P1

Há alterações em transações, Tesouro, Metas, IRPF, Resumo/Patrimônio, hooks e store.

O workflow da PR aprovou lint, typecheck e build do frontend no baseline auditado, mas a promoção ainda depende da rodada assistida sem P0/P1 da #303 e da revalidação dos findings #352/#354 quando aplicáveis.

### 6. Remoções e limpeza legacy — intenção confirmada

O diff contém remoções deliberadas do GOV-07:

- `.removed_code`;
- documentos históricos de raiz;
- cleanup antigo do Tesouro Educa+;
- writer TWR superseded;
- writer patrimonial simples de `PortfolioSnapshot`.

Essas remoções fazem parte da convergência arquitetural e não devem ser revertidas para reduzir o delta contra `main`.

### 7. CI/toolchain — sem alteração no delta da PR

A lista de arquivos alterados da PR não contém workflows, manifests de dependência ou configuração global de mypy. Portanto o gate vermelho observado usa o contrato de CI já existente; não é consequência de relaxamento ou mudança recente do workflow.

## Evidência do workflow da PR #362

Run `SIG v2 CI/CD` #831, id `34635549971`, no head `8c9580613b485475211982cc459c44a911fe40be`:

Aprovados:

- frontend lint;
- frontend typecheck;
- frontend build;
- flake8 backend;
- pip-audit;
- npm audit;
- Gitleaks;
- Trivy filesystem;
- lint dos Dockerfiles.

Falha:

- `mypy app`: 49 erros em 9 arquivos.

Como consequência, ficaram sem execução nesse run:

- fresh database migration gate;
- pytest backend.

Logo, o run #831 é evidência parcial útil, mas não é um gate de promoção aprovado.

## Finding imediato corrigido durante a auditoria

A contração do writer simples de snapshots expôs que `portfolio_snapshot_certification_cycle.py` ainda importava `calc_snapshot_at_date()` removido.

A correção foi feita sem reintroduzir o writer legado:

- `f87b805004b59c2aa310f4f243c3a7dfcad2ce33` — `backfill_canonical_snapshots_with_returns()` recebe `end_date` e `commit=False` opcionais para uso transacional/bounded;
- `2fed445ecebc5a02c22f5e0e393cc13913d7ca55` — o cycle de certificação passa a usar exclusivamente o writer canônico;
- `a7dfa09e7ca61ca52a154a6c0421b2cf77bc820c` — testes acompanham a fronteira canônica.

O objetivo foi preservar a certificação destrutiva controlada por savepoint sem criar uma segunda autoridade de escrita para `PortfolioSnapshot`.

## Gate P1 criado

Issue #363 — `[P1] Recuperar gate mypy do backend no SHA candidato`.

O run #831 concentrou os erros restantes em typing ORM/DTO e CLIs de certificação. O plano é corrigir por domínio em commits pequenos, sem `# type: ignore` global e sem enfraquecer `mypy app`.

## Blockers reais para promoção da PR #362

1. #363: backend mypy vermelho;
2. fresh migration gate ainda não executado com sucesso após o último delta;
3. pytest backend ainda não executado pelo workflow após o mypy vermelho;
4. #303 ainda não congelou SHA `PORTFOLIO-TEST-READY`;
5. #226 e #216 ainda precisam fechar decisão/reconciliação de Proventos;
6. #158 ainda precisa reconciliar dataset/SHA final e janela de promoção;
7. #269 precisa reconciliar segurança do SHA candidato;
8. #284 precisa homologar na OCI exatamente o SHA certificado localmente;
9. #227 continua sendo a decisão final GO/NO-GO para dados reais.

## Itens que não são blockers por si só

- 298 commits acumulados;
- 228 arquivos alterados;
- a existência da PR draft;
- ausência de conflito Git no estado atual (`mergeable=true`);
- features pós-GO já classificadas no backlog.

## Ordem objetiva de saneamento

1. recuperar `mypy app` sob #363;
2. executar localmente flake8/mypy/fresh migration gate/pytest no SHA resultante;
3. manter a PR #362 draft e usar seu CI somente como confirmação complementar;
4. continuar GOV-07D/E/F apenas sobre baseline suficientemente verde;
5. executar GOV-07H sincronizando README/ROADMAP/CHANGELOG e documentação arquitetural ao estado final;
6. concluir GOV-07I com correlação código↔tests↔Issues↔docs e SHA candidato;
7. seguir #303 → #226 → #216 → #158 → #269 → #284 → #227;
8. somente após GO avaliar promoção de `ready_for_real_data=true` e merge para `main`.

## Decisão

A divergência `stable-15jun` → `main` é grande, porém estruturalmente compreensível e atualmente mergeável. O impedimento imediato não é conflito de branches: é qualidade/certificação incompleta do SHA acumulado.

A PR #362 deve permanecer DRAFT até os gates acima estarem reconciliados.
