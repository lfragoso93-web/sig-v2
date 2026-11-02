# Operação de produção OCI

Estado vigente em 01/11/2026. Este runbook cobre observação e resposta a incidentes da produção. Releases normais são executados pelo GitHub Actions após CI aprovado para `main`; consulte [`oci-self-hosted-runner-runbook.md`](oci-self-hosted-runner-runbook.md). Não publique valores de secrets, tokens, dados pessoais ou conteúdo bruto de logs.

## Verificação de um release

Use a execução de `Deploy to OCI Production` vinculada ao CI que concluiu com sucesso para o push em `main`. Confirme no resumo/logs protegidos do workflow:

- branch de destino `main` e SHA alvo igual ao SHA do CI;
- backup pré-deploy concluído;
- checkout/`APP_COMMIT_SHA` igual ao SHA alvo;
- serviços, banco, Redis e smoke verificados;
- certificação de release persistida e `/ready` aprovado para a identidade atual.

`/health` verifica disponibilidade básica. Para dados reais, `/ready` é o gate autoritativo e deve permanecer fail-closed diante de divergência. CI isolado ou `/health=200` não comprovam release certificado.

## Incidente ou deploy malsucedido

1. Interrompa novos deploys enquanto avalia a execução falha.
2. Preserve os volumes e o backup pré-deploy. Não execute `docker compose down -v`, remoção/pruning de volumes, recriação do banco ou limpeza de artefatos como tentativa de recuperação.
3. Consulte logs e checks da execução, removendo segredos e dados pessoais antes de compartilhar qualquer trecho.
4. Para correção de código, reproduza localmente em `stable-15jun`, valide, abra PR para `main` e use o deploy automático.
5. Uma reversão de release deve passar por alteração revisada em `main` e pelo mesmo fluxo de CI/CD. Restauração de banco é uma ação separada, exige análise do backup e procedimento de recuperação aprovado; não a combine automaticamente com rollback de código.
6. Após a recuperação, confirme SHA, migration head, `/health` e `/ready`. Uma nova identidade requer nova certificação; nunca force readiness nem reutilize evento de outro SHA/dataset/schema.

## Limites

- Não fazer deploy por SSH, `git pull`, alteração manual do `.env` ou `docker compose up` em rotina normal.
- Não abrir portas ou alterar firewall para contornar falha de aplicação/tunnel.
- Não executar seeds, imports, rebuilds financeiros ou operações de dados como parte de um restart.
- Use [`oci-backup-restore-runbook.md`](oci-backup-restore-runbook.md) para distinguir backup automático de restauração controlada e [`../REAL_DATA_CERTIFICATION_RUNBOOK.md`](../REAL_DATA_CERTIFICATION_RUNBOOK.md) para gates de dados reais.
