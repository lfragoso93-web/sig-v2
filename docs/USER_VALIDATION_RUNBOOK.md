# Validacao local com usuarios - SGI v2

Estado vigente em 01/11/2026. Windows com Docker e o ambiente local de desenvolvimento e validacao; use a branch `stable-15jun` e a stack local configurada para desenvolvimento. OCI e producao, executa `main` e nao deve ser reconstruida a partir deste procedimento.

## Validacao local

1. Confirme que o checkout esta em `stable-15jun` e que a arvore de trabalho contem apenas as alteracoes pretendidas.
2. Confirme que o Docker Desktop Linux engine esta acessivel. Se nao estiver, marque a validacao de runtime como bloqueada; nao a declare aprovada.
3. Use o `.env` local; nunca copie secrets ou `.env` produtivo, nem conecte a aplicacao local ao banco de producao.
4. Inicie somente a stack base de desenvolvimento, sem o Compose de OCI:

   ```powershell
   docker compose -f docker-compose.yml up -d --build db redis backend frontend
   ```

   O Compose base e para uso local e nao inclui `cloudflared`. Nao passe `docker-compose.oci.yml` nem qualquer override de OCI. Acesse a aplicacao por `localhost`.
5. Execute as validacoes previstas e preserve dados/volumes locais. Se for necessario testar com copia de dados produtivos, restaure-a em banco isolado; nao sobrescreva o banco local existente. Nunca use `down -v`, remocao de volumes ou recriacao de bancos como etapa de validacao.
6. Ao terminar, inclusive se a validacao falhar, desligue a stack iniciada:

   ```powershell
   docker compose -f docker-compose.yml down
   ```

   Confirme que os servicos estao parados. Esse comando nao deve receber `-v`, para preservar volumes e dados locais.
7. Registre problemas funcionais sem incluir tokens, credenciais ou dados pessoais em Issues/logs compartilhados.
8. Depois da validacao, abra PR para `main`. O deploy OCI ocorre automaticamente somente apos merge e CI aprovado.

## Separacao de readiness

`user_test_readiness` e um diagnostico de testes assistidos. Ele nao certifica a producao nem altera `/ready`. OCI exige certificacao persistida vinculada a ambiente, branch, SHA, dataset e revision Alembic. Use `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` para esse contrato.

Os blocos datados abaixo neste arquivo foram substituidos por este procedimento e devem ser tratados como evidencias historicas, nao como instrucoes atuais de deploy ou endpoints de acesso.
