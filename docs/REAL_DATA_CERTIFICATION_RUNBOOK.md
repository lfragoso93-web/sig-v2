# Certificação persistente para dados reais — SGI v2

Issue: #384

Branch obrigatória: `stable-15jun`

Última atualização: 06/10/2026

## Estado e objetivo

Este runbook governa promoção e revogação auditáveis do estado de prontidão
para dados reais. Ele não executa bootstrap, seed, import, rebuild, migration,
reconciliação financeira nem escrita no ledger.

A fundação está implementada e promovida pelas PRs #386 e #387:

- `real_data_certification_events` append-only;
- leitor DB-first e relatório composto;
- evidência `real-data-promotion-evidence.v1`;
- plano determinístico e confirmação forte;
- executor transacional sob advisory lock PostgreSQL;
- CLI dry-run por padrão.

Em 06/10/2026, a promoção autorizada foi persistida para a identidade exata do
runtime no SHA `3ab054f61e34f440dddf93c170259958243d58af`; o `/ready` retornou
`200` com `ready_for_real_data=true`, inclusive após restart. A suíte opt-in em
PostgreSQL 16 efêmero também comprovou concorrência, stale-plan e restart sem
tocar o banco canônico. Qualquer novo SHA ou dataset exige outro ciclo completo
de evidência, dry-run, autorização e validação.

Para resolver a identidade, o runtime exige `ENVIRONMENT`, `APP_BRANCH`,
`APP_COMMIT_SHA` completo e `REAL_DATASET_REFERENCE`; a revision Alembic é lida
diretamente do banco. Campo ausente, `unknown`, múltiplos heads ou divergência
com o evento resultam em 503.

A referência canônica do dataset é derivada exclusivamente de um backup
`pre-prod-backup.v3` consistente e validado. Seu formato é
`pre-prod-backup.v3:sha256:<sha256-do-dump>`. Não usar nomes livres, timestamps,
contagens do inventário ou um backup histórico de outro estado do banco.

## Invariantes

- memória de processo não é fonte de verdade;
- o último evento persistido determina o estado auditável;
- eventos são imutáveis: revogar significa acrescentar um novo evento;
- `GO_ASSISTED` não é aceito como `GO`;
- a identidade inclui ambiente, branch, SHA completo, dataset, revision Alembic,
  gate #227 e PR #362;
- toda falha deve terminar com `database_writes_executed=0`;
- o chamador controla o commit; o executor apenas faz `flush`;
- nunca apagar eventos para desfazer uma decisão.

## Evidência de promoção

O arquivo JSON deve conter exatamente os checks obrigatórios:

```json
{
  "schema_version": "real-data-promotion-evidence.v1",
  "status": "GO",
  "dataset_reference": "DATASET-REFERENCE",
  "ready_for_real_data": false,
  "database_writes_executed": 0,
  "blockers": [],
  "warnings": [],
  "checks": {
    "readiness": true,
    "inventory": true,
    "services": true,
    "schema": true,
    "dataset_identity": true
  }
}
```

Não converter automaticamente a saída de `user-test-readiness.v1`. A evidência
acima é uma decisão própria da #384 e deve ser produzida somente após verificação
formal do dataset candidato.

## Preflight obrigatório

1. confirmar branch `stable-15jun`, SHA local/remoto e working tree limpa;
2. registrar ambiente, referência imutável do dataset e revision Alembic;
3. comprovar que a evidência se refere ao mesmo dataset e ao estado fechado;
4. confirmar `blockers=[]`, `warnings=[]` e zero escritas na coleta;
5. garantir que não há writer concorrente não autorizado;
6. preservar backup/restore e volumes existentes;
7. anexar o dry-run à #384 antes de solicitar execução real.

OCI/#284 não faz parte do caminho atual.

## Identidade canônica do dataset

Depois de alinhar aplicação e migrations e congelar writers não autorizados,
gere o backup `pre-prod-backup.v3` pelo fluxo de `docs/operations.md`. Em seguida,
derive a identidade sem alterar banco ou artefatos:

```powershell
$ArtifactDir = "/app/artifacts/pre-prod-rebuild/$RunId"
$DatasetIdentity = docker compose exec -T backend `
    python -m app.cli.real_data_dataset_identity `
    --artifact-directory $ArtifactDir | ConvertFrom-Json
$DatasetReference = $DatasetIdentity.dataset_reference
```

Aprovar somente quando:

- `schema_version=real-data-dataset-identity.v1`;
- `backup_schema_version=pre-prod-backup.v3`;
- branch e SHA do backup correspondem ao estado candidato;
- `database_writes_executed=0`;
- o checksum foi recalculado sobre `database.dump` e coincide com
  `backup-report.json` e `database.dump.sha256`;
- inventário read-only e listagem do dump estão presentes e válidos.

Qualquer mudança posterior no banco invalida a fotografia candidata e exige
novo backup. A identidade de um artefato histórico pode validar o contrato da
CLI, mas não identifica o dataset corrente.

## Dry-run de promoção

Coloque a evidência em
`artifacts/real-data-certification/evidence.json`. O Compose monta `artifacts`
em `/app/artifacts` no backend.

```powershell
$CommitSha = (git rev-parse HEAD).Trim()
$Evidence = "/app/artifacts/real-data-certification/evidence.json"

docker compose exec backend python -m app.cli.real_data_certification `
    --action promote `
    --environment local `
    --branch stable-15jun `
    --commit-sha $CommitSha `
    --dataset-reference $DatasetReference `
    --alembic-revision "ALEMBIC-REVISION" `
    --gate-issue-reference "#227" `
    --pull-request-reference "#362" `
    --evidence-file $Evidence `
    --actor "OPERATOR" `
    --reason "ISSUE-384"
```

Aprovar o dry-run somente quando:

- `schema_version=real-data-certification-cli.v1`;
- `mode=dry-run`;
- `database_writes_executed=0`;
- `transaction_committed=false`;
- identidade, hash, ação e referências conferem;
- `plan.confirmation` foi preservado sem alteração.

## Execução real

A promoção de 06/10/2026 foi executada com autorização operacional explícita.
Para uma promoção ou revogação futura, repetir o comando sobre o mesmo estado
do dry-run acrescentando:

```text
--execute --confirmation "<plan.confirmation exato do dry-run>"
```

Qualquer mudança de identidade, evidência ou evento predecessor invalida o
plano. Não ajustar a confirmação manualmente. O resultado aprovado deve
registrar uma escrita, transação commitada e a chave do evento esperado.

Depois da validação operacional, gere o resumo read-only versionado pelo fluxo
de `docs/CERTIFICATION_PROOF.md`. O proof não substitui o evento persistido nem
autoriza uma nova promoção.

## Revogação

Revogar é fail-closed e exige que exista promoção vigente para a mesma
identidade. A evidência de revogação deve registrar `blockers` como sequência e
explicar a causa. Use primeiro `--action revoke` sem `--execute`; a CLI vincula o
novo evento ao predecessor vigente. A execução segue a mesma confirmação forte.

Não atualizar ou remover a promoção anterior. Se não houver estado promovido, a
revogação deve falhar sem escrita.

## Concorrência, restart e stale plan

A suíte PostgreSQL que antecedeu a integração com `/ready` comprovou:

- duas execuções concorrentes não criam decisões conflitantes;
- advisory lock serializa a identidade alvo;
- mudança do último evento entre plano e execução rejeita o stale plan;
- restart do processo reconstrói o mesmo estado somente pelo banco;
- repetição idêntica é idempotente ou rejeitada sem nova escrita;
- rollback mantém o histórico anterior intacto.

Esses testes não devem promover o dataset corrente. Use transações revertidas,
fixtures isoladas ou banco temporário e confirme o estado antes/depois.

## Falha e recuperação

Em qualquer erro:

1. interromper a sequência;
2. confirmar `database_writes_executed=0` e `transaction_committed=false`;
3. preservar logs, JSON, SHA e identidade do dataset;
4. não repetir com `--execute` até corrigir e gerar novo dry-run;
5. se uma promoção já commitada se tornar inválida, criar revogação auditável.

Nunca usar remoção de volume, `docker compose down -v`, prune ou edição manual da
tabela como mecanismo de rollback.

## Saída do bloco

Registrar na #384:

- SHA completo e migration revision;
- identidade do dataset e hash da evidência;
- JSON do dry-run e confirmação emitida;
- testes PostgreSQL de concorrência/restart;
- estado anterior e posterior;
- `database_writes_executed` e `transaction_committed`;
- decisão explícita de manter ou integrar `/ready`.
