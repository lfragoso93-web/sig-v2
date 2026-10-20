# Ensaio administrativo de backup e restore (#83)

Atualizado em 17/10/2026. Este documento registra uma prova executada com o
backend atual e dois bancos PostgreSQL descartáveis em uma rede Docker isolada.
Nenhum dado, container ou volume operacional foi usado como origem ou destino.

## Resultado

O ensaio usou a imagem backend atual `sha256:27318c241d4b44843b649250a00fdd7dd16898ad6bfcc59607ddd2ff30cb7e41`.


O roteiro `backend/scripts/admin_backup_restore_http_rehearsal.py` executou o
fluxo pela API com operações reais de banco de dados:

- autenticação Bearer e autorização SuperAdmin reais contra a tabela `users`;
- `POST /api/v1/admin/database/backup` retornou 202, executou `pg_dump` em
  background e persistiu o estado final `succeeded`;
- `GET /api/v1/admin/database/backups/{filename}` retornou 200 com conteúdo
  gzip autenticado;
- `POST /api/v1/admin/database/restore` revalidou a senha, retornou 202, executou
  `psql` em background e persistiu o estado final `succeeded`;
- auditoria real persistiu uma ação `BACKUP` e uma ação `RESTORE`;
- um marcador sintético permaneceu na origem e foi restaurado no banco alvo que
  começou vazio.

Resultado resumido: `artifacts/admin-backup-restore/20261017-issue83/http-rehearsal.json`.
O ensaio estrutural de schema e reconciliação de inventário executado no mesmo
bloco está em `artifacts/admin-backup-restore/20261017-issue83/final.json` e
`schema-reconciliation.json`; esses relatórios confirmam 25 tabelas e igualdade
estrutural do schema restaurado.

## Isolamento do restore

Foram usados dois bancos efêmeros PostgreSQL 16 na mesma rede de teste:

1. origem descartável, migrada até `20261016_corp_ev_effective_date`, usada pela
   API para autenticação, auditoria e consulta de operações;
2. alvo descartável, sem schema SGI antes do restore.

O harness direciona a URL lida pelo endpoint de restore ao alvo vazio, mantendo
`get_db` e `AsyncSessionLocal` da API na origem descartável. Assim, testa a rota,
reautenticação, auditoria, persistência/status, fila background e serviço de
restore real, sem criar uma operação que sobrescreva o banco que guarda sua
própria autenticação e seu próprio status.

Isso deixa explícita uma limitação de produção já conhecida: o restore do
produto continua apontando para o mesmo banco da aplicação. A restauração pode
substituir a tabela de status e perder o estado final da operação; a execução
usa `BackgroundTasks` local ao processo e não possui worker durável/retry. O
ensaio não declara disaster recovery certificado nem elimina essas limitações.

## Reexecução

Execute somente em rede e bancos descartáveis. Migre a origem com o backend
versionado em teste, deixe o alvo vazio, e passe as duas URLs explicitamente ao
container do ensaio pelas variáveis `DATABASE_URL`, `ASYNC_DATABASE_URL` e
`ISSUE83_EMPTY_TARGET_DATABASE_URL`. A saída JSON deve ser preservada como nova
evidência; nunca configure essas variáveis com o `.env` ou host operacional.

O script retorna falha em qualquer status HTTP inesperado, status de operação
diferente de `succeeded`, ausência de auditoria ou divergência dos marcadores.
As credenciais no script são fixtures sintéticas e não devem ser reutilizadas
fora do container descartável.

## Decisão da Issue

O critério registrado na #83 — ensaio ponta a ponta em banco descartável, com
runbook e verificações de integridade, sem operar o banco real — foi atendido
com a prova HTTP e a prova estrutural complementar. Permanecem documentadas as
limitações de worker/status acima e a ausência de teste dedicado de componente
para `BackupPanel`; não são tratadas como sucesso de disaster recovery.
