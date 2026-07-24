# Runbook — execução controlada da limpeza de pré-produção

## Estado

Este documento define o gate de execução da Issue #199, vinculada à Issue-mãe
#158.

A PR #198 promoveu o executor transacional, a CLI e o ensaio integral em
PostgreSQL descartável. A PR #204 adicionou o perfil explícito de pré-produção
real sem duplicar o executor nem remover as proteções do perfil isolado.

A entrada operacional continua sendo:

```text
python -m app.cli.pre_prod_isolated_cleanup
```

Para a execução real em Windows/PowerShell, a entrada oficial do operador é o
wrapper versionado:

```text
scripts/Invoke-PreProdRealCleanup.ps1
```

O nome histórico da CLI não restringe o alvo ao ambiente isolado. O alvo é
definido exclusivamente pelo marcador validado pelo contrato.

Nenhuma cadeia produzida antes da promoção da PR #204 pode autorizar uma
execução real, porque branch, SHA completo, `run_id` e checksum canônico do plano
fazem parte da autorização. A cadeia `20260724-100752` é evidência histórica e
não pode ser reutilizada.

## Escopo

Este runbook cobre:

- execução em banco isolado restaurado de backup;
- execução na pré-produção real após autorização humana explícita;
- validações anteriores à primeira escrita;
- transação, rollback, publicação de evidências e reconciliação imediata;
- handoff para os blocos posteriores da Issue #158.

Este runbook não autoriza:

- gerar ou alterar o plano durante a execução;
- editar artefatos manualmente;
- executar seed, coleta, importação ou rebuild no mesmo bloco;
- alterar schema;
- usar `TRUNCATE`, `CASCADE`, DDL ou comandos paralelos;
- promover automaticamente uma autorização isolada para o perfil real;
- executar a limpeza sem nova cadeia vinculada ao SHA corrente.

## Perfis de alvo suportados

A CLI aceita somente dois marcadores:

| Marcador | Relação entre origem e destino | Uso |
| --- | --- | --- |
| `sgi-pre-prod-isolated` | identidades normalizadas diferentes | ensaio em banco descartável restaurado |
| `sgi-pre-prod-real` | identidades normalizadas exatamente iguais | limpeza autorizada da pré-produção real |

A identidade normalizada é composta por host, porta e nome do banco. Qualquer
outro marcador aborta antes da criação do engine e antes de qualquer escrita.

No perfil isolado, origem igual ao destino é recusada. No perfil real, origem
diferente do destino é recusada. Os dois perfis preservam os mesmos gates de
plano, confirmação, contagens, lock, transação, rollback e evidências.

## Argumentos da CLI

Argumentos obrigatórios:

- `--plan`;
- `--branch stable-15jun`;
- `--commit-sha <sha-completo-de-40-caracteres>`;
- `--source-database-url <url-postgresql-sincrona>`;
- `--target-database-url <url-postgresql-sincrona>`;
- `--target-isolation-marker <sgi-pre-prod-isolated|sgi-pre-prod-real>`;
- `--confirmation "<texto-composto>"`.

Argumento opcional:

- `--artifact-root`, com o diretório raiz dos artefatos.

O argumento `--rehearsal-fail-after-table` existe exclusivamente para ensaio
controlado de rollback. Ele é proibido na execução real.

URLs completas não devem aparecer em logs, Issues ou artefatos. As evidências
persistem somente a identidade redigida `host:port/database`.

## Cadeia obrigatória de artefatos

Imediatamente antes da janela real, gerar uma nova cadeia com um único `run_id`,
branch `stable-15jun` e o mesmo SHA completo:

1. backup `pre-prod-backup.v3`;
2. inventário da origem vinculado ao snapshot;
3. exportação `pre-prod-export.v1`;
4. impacto `pre-prod-cleanup-impact.v2` em modo read-only;
5. plano `pre-prod-cleanup-execution.v1` em modo `plan`.

A cadeia deve confirmar:

- backup restaurável, snapshot consistente e checksum válido;
- exportação completa e `reconciled=true`;
- 24 tabelas classificadas, sem tabelas desconhecidas;
- 11 tabelas preservadas, 3 exportáveis e 10 reconstruíveis;
- zero blockers e zero ciclos;
- `database_accessed=false` no planejamento;
- `database_writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`;
- `plan_only=true`;
- ausência de sobrescrita de artefatos.

Os números acima pertencem ao inventário canônico atual. Qualquer divergência
exige nova auditoria; não deve ser normalizada manualmente.

## Gates antes da primeira escrita

A execução deve abortar quando qualquer condição falhar:

- `stable-15jun` não estiver sincronizada com a `main` promovida;
- working tree estiver suja;
- SHA executado divergir do SHA registrado no plano;
- `run_id` estiver ausente, reutilizado ou incompatível;
- contrato ou modo do plano forem diferentes dos aprovados;
- checksum canônico do plano ou de seus artefatos divergir;
- houver blockers, ciclos ou classificação desconhecida;
- as contagens atuais divergirem de `expected_rows_before`;
- o perfil não corresponder à relação entre origem e destino;
- o driver não for PostgreSQL síncrono;
- a confirmação composta não for exata;
- o lock operacional não puder ser adquirido;
- houver coleta, seed, importação, rebuild ou outro processo concorrente;
- backup ou restauração emergencial não estiverem disponíveis;
- qualquer artefato tiver sido alterado manualmente.

## Confirmação composta

Formato exato:

```text
CLEANUP <run-id> ON <database> AT <commit-sha> WITH <plan-sha256>
```

A confirmação vincula o `run_id`, o nome do banco de destino, o SHA completo e o
checksum canônico do plano. Ela deve ser recalculada a partir da nova cadeia,
revisada visualmente e registrada como autorização humana explícita na Issue
#199 antes da execução real.

Use exclusivamente o campo `plan_sha256` emitido por
`python -m app.cli.pre_prod_cleanup_plan`. O campo pertence ao envelope exibido
pela CLI e não ao próprio `plan.json`. Não use `Get-FileHash`: a autorização é
validada contra a serialização JSON canônica.

Uma confirmação anterior não pode ser reutilizada para outro `run_id`, SHA,
banco ou checksum.

## Execução controlada

### Perfil isolado

Usar `sgi-pre-prod-isolated`, com origem e destino diferentes, somente em banco
descartável restaurado. O perfil pode usar a falha controlada de ensaio quando o
objetivo explícito for comprovar rollback.

### Perfil real

Usar `sgi-pre-prod-real` e fornecer URLs que representem exatamente a mesma
identidade normalizada de pré-produção em origem e destino.

O wrapper oficial fixa branch, módulo e marcador, usa a mesma URL síncrona para
origem e destino, preserva cada parâmetro como um único argumento e propaga sem
alteração o exit code da CLI. A URL deve existir somente na variável de ambiente
`PRE_PROD_SYNC_DATABASE_URL`.

Antes da chamada:

1. revisar o plano e o checksum canônico;
2. registrar a autorização humana na Issue #199;
3. confirmar a janela sem processos concorrentes;
4. confirmar backup e restauração emergencial;
5. confirmar que `--rehearsal-fail-after-table` não está presente.

Executar em PowerShell a partir da raiz do repositório:

```powershell
$env:PRE_PROD_SYNC_DATABASE_URL = "<url-postgresql-sincrona>"

.\scripts\Invoke-PreProdRealCleanup.ps1 `
    -PlanPath $PlanPath `
    -CommitSha $CommitSha `
    -Confirmation $Confirmation

$CleanupExitCode = $LASTEXITCODE
```

O valor de `Confirmation` deve ser o texto composto já revisado e autorizado;
o wrapper não o calcula nem o corrige. O parâmetro opcional `-ArtifactRoot`
permite alterar a raiz padrão `artifacts/pre-prod-rebuild`.

Não usar invocação direta, `python -c`, `sh -lc`, `Invoke-Expression` ou comandos
PowerShell aninhados para construir ou executar a confirmação real.

## Estratégia transacional

O executor:

1. revalida plano, identidade, perfil e confirmação antes de criar o engine;
2. captura as contagens anteriores;
3. abre uma transação controlada;
4. adquire o lock operacional;
5. revalida `expected_rows_before`;
6. executa `DELETE` somente na ordem canônica do plano;
7. valida as pós-condições;
8. efetiva `COMMIT` apenas após todas as validações;
9. executa `ROLLBACK` integral diante de falha;
10. publica evidências redigidas sem sobrescrever artefatos existentes.

A ordem não é mantida em uma segunda lista no runbook ou na CLI. A única ordem
executável vem do plano aprovado e é revalidada pelo contrato.

## Artefatos da execução

O relatório principal é publicado em:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup/execution.json
```

Quando aplicável, a execução também publica:

- `preserved-before.json`;
- `preserved-after.json`;
- `post-cleanup-inventory.json`;
- `reconciliation.json`.

As evidências devem registrar estado final, timestamps, alvo redigido, checksum
do plano, contagens antes e depois, ordem executada, lock, commit ou rollback e
motivo de aborto. Credenciais e a confirmação literal não são persistidas.

## Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | sucesso, commit e evidências publicados |
| `1` | falha interna não classificada |
| `2` | entrada ou JSON inválido |
| `10` | identidade, branch, SHA ou plano divergente |
| `11` | alvo, marcador ou driver inválido |
| `12` | confirmação composta inválida |
| `20` | contagens ou plano divergentes antes da escrita |
| `21` | lock operacional indisponível |
| `22` | execução revertida por falha ou pós-condição |
| `30` | falha de publicação ou reconciliação auditável |
| `130` | interrupção pelo operador |

Qualquer código diferente de zero bloqueia os blocos seguintes e deve ser
registrado na Issue #199 antes de nova tentativa.

## Reconciliação imediata

Após código zero, confirmar:

- `final_state=committed`;
- `committed=true`;
- tabelas planejadas zeradas;
- tabelas preservadas e fora do plano inalteradas;
- `reconciliation.ok=true`;
- ausência de alteração de schema;
- ausência de credenciais nos artefatos;
- ausência de seed, coleta, importação ou rebuild durante a limpeza.

Se qualquer item divergir, interromper a janela, preservar evidências e aplicar o
procedimento de restauração emergencial. Não iniciar correções ad hoc no banco.

## Handoff para a Issue #158

Somente após a limpeza real reconciliada:

1. autorizar seed B3 COTAHIST em bloco separado;
2. autorizar seed oficial do Tesouro Direto;
3. autorizar benchmarks, câmbio e proventos;
4. importar o CSV completo da carteira;
5. reconstruir posições e snapshots;
6. executar reconciliação financeira e auditoria de cobertura;
7. validar Resumo, Patrimônio, Rentabilidade, Proventos e importação.

## Referências

- Issue-mãe: #158;
- gate operacional: #199;
- executor e ensaio isolado: Issue #196 e PR #198;
- perfil real: PR #204;
- contrato: `backend/app/services/pre_prod_isolated_cleanup_contract.py`;
- CLI: `backend/app/cli/pre_prod_isolated_cleanup.py`;
- wrapper real: `scripts/Invoke-PreProdRealCleanup.ps1`;
- perfil de alvo real: `docs/pre-prod-real-cleanup-target-profile.md`;
- runbook geral: `docs/PRE_PROD_REBUILD_RUNBOOK.md`.
