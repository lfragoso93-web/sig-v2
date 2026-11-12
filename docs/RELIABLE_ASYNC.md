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
| cotações gerais 09:00–18:00 e cripto fora desse intervalo | ativo | alto: provider, preços e cache globais | leases Redis por lote, TTL 7200s, liberação ao concluir |
| fechamento diário global de preços | ativo | alto: backfill e writes globais | lock Redis implementado |
| fechamento diário do Tesouro | ativo | alto: import e latest prices compartilhados | lock Redis implementado |
| manutenção de snapshots/TWR | ativo | médio: rebuild derivado e idempotente | lock Redis global implementado |
| `rate_history` BCB | ingestão canônica pelo `benchmark_rate_service`; módulo legado não registrado removido | protegido pelo lock do job de benchmarks | não criar segundo coletor |
| startup bootstrap | assíncrono, não recorrente | mitigado por reserva e locks DB por estágio | manter contrato atual |
| backfills após transação/CSV | BackgroundTasks locais | médio, derivados reconstruíveis | sem outbox neste momento |

## Agendamentos recorrentes ativos

Todos os horários usam `America/Sao_Paulo`. O cadastro está em
`backend/app/core/scheduler.py`; as tarefas globais usam lease Redis para
impedir execução concorrente entre réplicas.

| Job | Horário | Escopo |
| --- | --- | --- |
| `sync_asset_dividends_morning` | segunda a sábado, 08:00 | Proventos; janela móvel de 90 dias para trás e 365 dias para frente. |
| `notify_daily_dividend_payments` | segunda a sexta, 08:30 | E-mail dos pagamentos do dia; não coleta dados de provedores. |
| `sync_benchmark_rates_daily` | segunda a sexta, 08:40 e 20:40 | CDI, Selic, IPCA e IGP-M; depende de `ENABLE_DAILY_BENCHMARK_SYNC`. |
| `sync_ibov_benchmark_daily` | segunda a sexta, 08:42 e 20:42 | Fechamento do Ibovespa; depende da mesma configuração. |
| `sync_corporate_events_daily` | segunda a sexta, 22:00 | Coleta eventos corporativos globais com savepoints por ativo (`continue_on_asset_error=True`) para não abortar o lote em falhas transitórias unitárias; não aplica eventos ao ledger. |
| `portfolio_snapshot_auto_maintenance` | diariamente, 21:00 | Reconstrói snapshots patrimoniais/TWR com dados persistidos; lock Redis global. |

Proventos e eventos reutilizam os estágios canônicos, com persistência
idempotente e sem alterar transações ou projeções de carteira. A consulta Yahoo
de proventos fica restrita à janela recorrente, sem baixar o histórico desde
1970 a cada execução.

## Estado e alerta operacional dos jobs

Cada execução que adquire a lease Redis registra `running`, `succeeded` ou
`failed`, início, fim, duração e tipo da exceção em uma hash Redis com retenção
de 90 dias. O payload da exceção não é persistido. Depois do registro, uma
exceção sanitizada com o tipo original é relançada ao APScheduler, sem a
mensagem original, para não parecer sucesso silencioso nem expor detalhes de
provedores no traceback do scheduler.

As gravações de status usam Lua para confirmar atomicamente que a execução
ainda possui a lease; os estados finais também conferem o token da execução na
hash. Um job antigo cujo TTL expirou não pode sobrescrever o estado de uma
execução que readquiriu a lease. Os lotes de cripto mantêm uma identidade de
status própria no painel, embora compartilhem a lease de cotações intradiárias.

O SuperAdmin consulta a próxima execução e o último resultado em
**Administração > Tarefas agendadas** (`GET /api/v1/admin/scheduler/status`).
O painel mostra um alerta visual para falha e indisponibilidade do Redis. Esse
alerta aparece enquanto o painel está aberto; não há envio de e-mail ou
notificação externa para falhas de jobs. A indisponibilidade do Redis continua
fail-closed para as tarefas com lease e deixa o histórico temporariamente
indisponível.

O job mensal de auditoria da fonte B3 segue desativado por padrão. Ele só deve
ser habilitado com URL e ano oficiais vigentes; sua auditoria é read-only e
não promove fatos para `market_calendar_days`.

## Lock distribuído adotado

O job `persist_daily_close_prices` usa uma lease Redis:

```text
SET sgi:job:persist_daily_close_prices:daily <owner-token> NX EX 7200
```

O job `portfolio_snapshot_auto_maintenance` usa a mesma semântica, com a key
`sgi:job:portfolio_snapshot_auto_maintenance:daily`, antes de abrir a sessão
que reconstrói snapshots derivados.

O lote geral atualiza cotações às horas cheias entre 09:00 e 18:00 em dias
úteis, incluindo cripto. Fora desse intervalo, um lote separado atualiza apenas
cripto de hora em hora, inclusive nos fins de semana. Cada lote usa uma lease
Redis com TTL de 7200 segundos, liberada ao concluir. Assim, uma execução
anterior ainda ativa impede sobreposição entre réplicas; quando termina, a
próxima janela horária pode iniciar. O fechamento do Tesouro usa
`sgi:job:persist_treasury_daily_close:daily` antes de abrir a sessão de banco.
O fechamento do Tesouro e os fechamentos diários continuam com TTL de duas horas.

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
