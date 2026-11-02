# Validacao local com usuarios - SGI v2

Estado vigente em 01/11/2026. Windows com Docker e o ambiente local de desenvolvimento e validacao; use a branch `stable-15jun` e a stack local configurada para desenvolvimento. OCI e producao, executa `main` e nao deve ser reconstruida a partir deste procedimento.

## Validacao local

1. Confirme que o checkout esta em `stable-15jun` e que a arvore de trabalho contem apenas as alteracoes pretendidas.
2. Use o `.env` local e os Compose de desenvolvimento documentados pelo projeto; nao copie secrets ou `.env` produtivo para a maquina local.
3. Valide a aplicacao localmente e preserve dados/volumes locais. Nao use `down -v`, remocao de volumes ou recriacao de bancos como etapa de validacao.
4. Registre problemas funcionais sem incluir tokens, credenciais ou dados pessoais em Issues/logs compartilhados.
5. Depois da validacao, abra PR para `main`. O deploy OCI ocorre automaticamente somente apos merge e CI aprovado.

## Separacao de readiness

`user_test_readiness` e um diagnostico de testes assistidos. Ele nao certifica a producao nem altera `/ready`. OCI exige certificacao persistida vinculada a ambiente, branch, SHA, dataset e revision Alembic. Use `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` para esse contrato.

Os blocos datados abaixo neste arquivo foram substituidos por este procedimento e devem ser tratados como evidencias historicas, nao como instrucoes atuais de deploy ou endpoints de acesso.
