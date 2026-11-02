# Producao OCI do SGI v2

Estado vigente em 01/11/2026. OCI e o ambiente produtivo e executa `main`. O ambiente Windows local e usado para desenvolvimento em `stable-15jun`.

## Release

O fluxo normal e Pull Request para `main`, CI aprovado e deploy automatico pelo workflow `.github/workflows/deploy-oci.yml` apos o push. O workflow fixa o SHA aprovado, salva backup pre-deploy, sincroniza `APP_COMMIT_SHA`, reconstrui a aplicacao, valida saude/servicos/smoke e executa a certificacao automatica do release. A execucao so termina com sucesso quando `/ready` confirma a identidade persistida para ambiente, branch, SHA, dataset e revision Alembic.

Nao usar deploy manual por SSH, `git pull`, edicao manual do `.env` ou `docker compose up` para releases normais. Falhas de codigo devem voltar ao ambiente local e seguir por PR. A restauracao de banco e independente de rollback de codigo e deve seguir seu procedimento controlado.

`/health=200` indica saude basica, nao certificacao. `/ready` deve permanecer fail-closed diante de divergencia. Se a automacao nao puder ancorar o dataset anterior valido ou se o dataset mudar, interrompe sem certificar; siga o ciclo completo em `../REAL_DATA_CERTIFICATION_RUNBOOK.md`.

## Seguranca operacional

Mantenha os servicos de dados sem exposicao publica; nao abra portas de aplicacao como contorno para falha. Nao compartilhe secrets, tokens, dados pessoais ou logs brutos. Backups e volumes existentes devem ser preservados durante deploy e recuperacao.

## Documentos

- `oci-execution-index.md`: fluxo e fontes operacionais vigentes.
- `oci-self-hosted-runner-runbook.md`: gatilhos e gates de CI/CD.
- `oci-operations-runbook.md`: observacao e resposta a falhas.
- `oci-backup-restore-runbook.md`: backup automatico e restauracao controlada.
- `oci-first-deploy-runbook.md` e `oci-smoke-test-runbook.md`: registros de provisionamento/laboratorio; nao usar para deploy atual de producao.
