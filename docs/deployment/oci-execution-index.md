# Índice operacional de produção OCI

Estado vigente em 01/11/2026. OCI é o ambiente produtivo do SGI v2 e acompanha a branch `main`. Windows com Docker é o ambiente local de desenvolvimento, na branch `stable-15jun`.

## Release normal

1. Desenvolver e validar localmente em `stable-15jun`.
2. Abrir PR para `main`; o CI valida o candidato e as proteções da branch controlam o merge.
3. Após merge/push em `main` e CI concluído com sucesso, `.github/workflows/deploy-oci.yml` inicia o deploy automático para OCI no SHA exato aprovado.
4. O workflow salva backup pré-deploy, atualiza o checkout e `APP_COMMIT_SHA`, reconstrói a aplicação e executa health, dependências, smoke e certificação automática da identidade do release.
5. O deploy só termina com sucesso quando `/ready` confirma a certificação persistida para o ambiente, branch, SHA, dataset e revisão Alembic atuais.

Não atualize a produção manualmente por SSH, `git pull`, Compose ou edição do `.env` para releases normais. Não faça push direto em `main`. Uma falha de deploy/certificação exige diagnóstico e correção pelo fluxo de PR; se a âncora do dataset estiver inválida ou tiver mudado, siga o ciclo manual de certificação descrito em [`../REAL_DATA_CERTIFICATION_RUNBOOK.md`](../REAL_DATA_CERTIFICATION_RUNBOOK.md).

## Referências vigentes

- [`oci-self-hosted-runner-runbook.md`](oci-self-hosted-runner-runbook.md) — gatilhos, gates e comportamento da automação.
- [`oci-operations-runbook.md`](oci-operations-runbook.md) — observação e resposta operacional segura.
- [`../REAL_DATA_CERTIFICATION_RUNBOOK.md`](../REAL_DATA_CERTIFICATION_RUNBOOK.md) — identidade, `/ready` e exceções que exigem certificação completa.
- [`oci-backup-restore-runbook.md`](oci-backup-restore-runbook.md) — política de backup automático e restauração controlada.

Os runbooks de provisionamento e laboratório descrevem procedimentos históricos ou de infraestrutura isolada; não são caminhos de release de produção.
