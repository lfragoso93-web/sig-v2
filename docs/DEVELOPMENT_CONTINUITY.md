# Continuidade de desenvolvimento — SGI v2

> Documento de retomada do trabalho. Baseline atualizada em 17/10/2026; ver
> `docs/DEVELOPMENT_BASELINE_2026-10-16.md` para evidências e artefatos.

## Estado atual

- Branch obrigatória: `stable-15jun`.
- O último SHA remoto observado era `b37661921e3a8455f45c8b676b28955d6ad3d0ea`.
  A identidade exata do runtime e do checkout corrente está no proof allowlisted
  em `artifacts/certification-proof/`.
- GitHub compara `stable-15jun` como 7 commits à frente e 0 atrás de `main`
  (`4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`); nenhuma PR estava aberta.
- O working tree não está limpo. A inspeção inicial identificou 15 alterações
  preexistentes e cinco itens não rastreados, incluindo código/migration de
  eventos corporativos, UI/testes de frações pendentes e artefatos temporários.
  Esta rebaseline acrescentou documentação. Não descartar, substituir ou incluir
  artefatos temporários em commit sem identificar seu uso.
- Na observação anterior ao deploy, backend/PostgreSQL/Redis estavam saudáveis;
  `/health=200` e `/ready=503` por `runtime_identity_error`.
- O backend/frontend candidatos foram implantados em `production`; a migration
  `20261016_corp_ev_effective_date` está aplicada. `/health=200`, readiness
  assistida `GO_ASSISTED` sem blockers/warnings e zero escritas.
- `/ready=503` continua fail-closed porque o evento persistido anterior diverge
  em SHA, dataset e Alembic. Proof e dry-run #384 confirmaram a identidade; o
  dry-run não escreveu e aguarda autorização explícita para promoção.
- Validacao do checkout em 17/10: suite backend completa com 2.401 passed, 5 skipped e 0 failed; flake8 e mypy passaram (411 arquivos); Architecture Doctor passou (6/6); migrations completas e drift gate passaram em PostgreSQL 16 descartavel. A execucao foi isolada, sem rede, com a arvore somente leitura.
- A suite frontend (171 testes, typecheck e lint) passou na verificacao de 16/10.
- Os gates backend/frontend e Doctor passaram; backup v3 e restore isolado
  reconciliaram. O candidato está implantado. A promoção #384 é o único passo
  pendente desta rodada e exige autorização para o plano atual.

## Próximo caminho

1. Consolidar a atualização factual em novo SHA; repetir backup v3, restore,
   gates, Doctor, proof e dry-run #384, pois o SHA muda.
2. Revisar a confirmação exata do plano atualizado e executar somente após
   autorização explícita; então comprovar `/ready` e persistência após restart.
3. Fechar os gates residuais #408 (CodeQL), #83 (backup/restore isolado) e GOV-07
   da #293; então escolher uma única entrega de produto.

## Mapa de Issues abertas

- Gate financeiro/factual: #149 e #370.
- Segurança, backup e governança: #408, #83 e #293.
- Schema: #272.
- OCI, backlog fora do caminho local: #284.
- Providers/bootstrap: #127, #130 e #253.
- UX e detalhe de ativo: #58, #90, #351 e #353.
- Renda Fixa e ferramentas: #355–#359.
- Metas, Analysis Engine e IA: #246, #360 e #361.
- OAuth: #97.

O inventário de 16/10 encontrou 23 Issues abertas e nenhuma PR aberta. Consulte
`docs/ISSUE_GOVERNANCE.md` para os estados e dependências, e o inventário
GitHub ao vivo antes de encerrar ou reordenar trabalho.

## Contratos que permanecem obrigatórios

- `transactions` é a fonte canônica do lifecycle financeiro; não reconstruir
  ledger paralelo para Tesouro, Renda Fixa ou eventos corporativos.
- Leituras financeiras são DB-first; ausência de preço, FX, evidência de evento
  ou cobertura fica explícita, sem inventar valores ou datas.
- Eventos corporativos conflitantes ou com liquidação não comprovada ficam fora
  da projeção canônica; transações históricas não são mutadas.
- Backups e seeds operacionais precisam ser auditáveis e vinculados ao SHA e
  dataset exatos.
- A promoção #384 é append-only e DB-first. `GO_ASSISTED` não promove dados
  reais; `/ready` fica fechado quando a identidade diverge ou está incompleta.
- Não usar `docker compose down -v`, remoção de volume, prune de volumes,
  `git reset --hard`, `git clean`, rebase de histórico publicado ou force-push.

## Documentação canônica

- `docs/DEVELOPMENT_BASELINE_2026-10-16.md` — fotografia do checkout e runtime.
- `ROADMAP.md` — sequência de desenvolvimento.
- `docs/ISSUE_GOVERNANCE.md` — hierarquia e estados das Issues.
- `docs/architecture.md` e `docs/CORPORATE_ACTIONS.md` — contratos vivos.
- `docs/USER_TEST_READINESS_GATE.md` e `docs/USER_VALIDATION_RUNBOOK.md` —
  testes assistidos.
- `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` e `docs/CERTIFICATION_PROOF.md` —
  identidade e certificação persistente.
- `docs/operations.md` e `docs/PRE_PROD_REBUILD_RUNBOOK.md` — backup e operação.

Changelogs e documentos em `docs/changelog/` preservam evidência histórica; não
devem ser reescritos como se descrevessem o runtime atual.
