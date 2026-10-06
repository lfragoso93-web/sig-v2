# Certification Proof do SGI v2

O contrato `sgi-certification.v1` resume, em JSON validável e associado ao SHA,
o estado observado de uma certificação. Ele é somente leitura: não promove,
revoga, executa migrations nem altera o banco.

## Evidência de testes

Crie um arquivo local fora do versionamento, por exemplo
`artifacts/certification-proof/tests.json`:

```json
{
  "contract": "sgi-certification-tests.v1",
  "suites": [
    {"name": "backend", "status": "passed", "required": true},
    {"name": "frontend", "status": "passed", "required": true}
  ]
}
```

O contrato aceita somente `name`, `status` e `required`; logs, comandos,
variáveis e campos extras são rejeitados para impedir que segredos sejam
copiados ao proof. Estados válidos são `passed`, `failed`, `skipped` e `error`.

## Geração

Execute no backend do runtime que está sendo comprovado:

```powershell
$CommitSha = (git rev-parse HEAD).Trim()
docker compose exec -T backend python -m app.cli.certification_proof `
    --checkout-sha $CommitSha `
    --tests-file /app/artifacts/certification-proof/tests.json `
    --output /app/artifacts/certification-proof/sgi-certification.v1.json `
    --disabled-optional-gate oci-284
```

A CLI executa o Architecture Doctor estático, consulta a identidade do runtime,
a revision Alembic e o evento persistido, e testa PostgreSQL e Redis. Redis é
reportado como opcional, coerente com `/health`; backend e PostgreSQL são
obrigatórios. O exit code é `0` apenas para `result=passed`, `1` para prova
válida mas reprovada e `2` para entrada/contrato inválido.

## Semântica fail-closed

O resultado não pode ser `passed` quando:

- `checkout_sha` diverge do `APP_COMMIT_SHA` do runtime;
- o último evento DB-first não certifica exatamente a identidade corrente;
- uma suíte obrigatória não passou;
- o Architecture Doctor falhou, pulou ou não conseguiu executar um finding;
- backend, PostgreSQL ou outro serviço marcado como obrigatório não está saudável.

`generated_at_utc` é o único campo volátil declarado. O restante identifica o
ambiente, branch, SHAs, dataset, revision Alembic, evento e gates observados.
O proof não substitui logs detalhados, backup, evidência de promoção ou o
histórico append-only de certificação.
