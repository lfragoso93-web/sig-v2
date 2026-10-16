# Reliable Async: scheduler locks e decisão de outbox

> ADR em 06/10/2026 para a Issue #350.

## Contexto

O `max_instances=1` do APScheduler impede concorrência somente dentro de um
processo. Duas réplicas do backend registram os mesmos jobs e podem executar o
mesmo trabalho simultaneamente. Redis e PostgreSQL já pertencem ao stack; não é
necessária uma dependência de mensageria adicional.

## Inventário e risco

| Job/efeito | Estado | Risco concorrente | Decisão |
| --- | --- | --- | --- |
| cotações intraday, dois triggers | ativo | alto: provider, preços e cache globais | candidato seguinte a lock |
| fechamento diário global de preços | ativo | alto: backfill e writes globais | lock Redis implementado |
| fechamento diário do Tesouro | ativo | alto: import e latest prices compartilhados | migrar em bloco próprio |
| manutenção de snapshots/TWR | ativo | médio: rebuild derivado e idempotente | lock Redis global implementado |
| rate history BCB | módulo registrável, fora do scheduler canônico | alto se ativado | exigir lock antes de ativar |
| startup bootstrap | assíncrono, não recorrente | mitigado por reserva e locks DB por estágio | manter contrato atual |
| backfills após transação/CSV | BackgroundTasks locais | médio, derivados reconstruíveis | sem outbox neste momento |

## Lock distribuído adotado

O job `persist_daily_close_prices` usa uma lease Redis:

```text
SET sgi:job:persist_daily_close_prices:daily <owner-token> NX EX 7200
```

O job `portfolio_snapshot_auto_maintenance` usa a mesma semântica, com a key
`sgi:job:portfolio_snapshot_auto_maintenance:daily`, antes de abrir a sessão
que reconstrói snapshots derivados.

- aquisição é fail-closed: Redis indisponível ou lock ocupado pula a execução;
- TTL de duas horas limita o bloqueio após crash/restart;
- a liberação usa Lua compare-and-delete e nunca remove a lease de outro owner;
- expiração permite nova aquisição sem deadlock permanente;
- `max_instances=1` continua útil no processo, mas não é a autoridade global;
- lock não substitui UPSERTs, constraints ou idempotência do job protegido.

Os logs estruturados distinguem `scheduler_lock_acquired`,
`scheduler_lock_refused`, `scheduler_lock_released`, expiração/reaquisição e
`reprocessing=True` quando `attempt > 1`. Tokens de ownership não são logados.

## Decisão sobre transactional outbox

Status: **não adotar agora**.

Os efeitos assíncronos examinados são reconstruções derivadas de snapshots e
invalidações de cache. Eles não publicam mensagem externa nem criam obrigação
irreversível que precise ser atômica com a escrita de domínio. Adicionar tabela,
worker, retry ledger e migration agora aumentaria a complexidade sem resolver
um caso aprovado.

O risco atual de BackgroundTasks perdidas após o commit é conhecido: snapshots
e caches podem ficar temporariamente defasados, mas são reconstruíveis pelos
serviços canônicos e não constituem o ledger financeiro. Esta decisão não os
declara ideais; apenas rejeita usar outbox antes de existir um evento concreto.

Reavaliar outbox quando uma escrita precisar, na mesma transação PostgreSQL,
garantir a publicação de trabalho durável como notificação externa, webhook,
integração contábil ou outro efeito não reconstruível. Nesse caso:

1. dado de domínio e registro outbox devem compartilhar o mesmo commit;
2. o consumidor deve ser idempotente e operar com semântica at-least-once;
3. claim, retry, backoff, dead-letter e observabilidade devem ter contrato;
4. uma migration e um worker só entram após issue e caso de uso aprovados.

## Validação

```powershell
cd backend
$env:ENVIRONMENT = "development"
..\.venv\Scripts\python.exe -m pytest tests/test_distributed_job_lock.py tests/test_scheduler.py tests/test_scheduler_provider_boundary.py -q -p no:cacheprovider
```

## Administrative backup and restore operations (#83)

Administrative backup and restore now keep a queryable record in
`admin_backup_operations`, with `queued`, `running`, `succeeded`, and `failed`
states. The endpoint is restricted to SuperAdmins and does not expose database
URLs, stderr, or local paths. This record complements `AuditLog`, which remains
the actor and request trail.

The executor still uses process-local `BackgroundTasks`; a crash can leave an
operation `queued` or `running`. This block adds neither a durable worker nor
automatic reprocessing. For restore, `running` is committed before `psql`
replaces the database. The restored backup can remove or revert its own status
row; the application attempts to write a final result if the table remains
available, but a missing row proves neither success nor failure. Do not treat
this history as certified disaster-recovery evidence. Restoring a dump from
before this migration may also remove the table; the status endpoint then
returns `503` and new administrative operations fail closed until schema
compatibility is restored through the approved migration process.

Successful administrative backups trigger retention cleanup. The default
window is 24 hours and can be changed with the positive integer setting
`ADMIN_BACKUP_RETENTION_HOURS`. Cleanup removes only regular files with the
canonical `backup_YYYYMMDD_HHMMSS.sql.gz` name whose filesystem modification
time is older than the window. Symlinks and unrelated files are left alone.
Cleanup failures are logged and do not change a completed backup's result.
This short operational retention is separate from certified pre-production
backup artifacts, which are stored and governed by their own runbook.
