# Runtime determinístico do SGI v2

A #349 estabelece três contratos incrementais: relógio injetável em lógica
financeira sensível a datas, configuração crítica validada no startup e budgets
de queries para detectar regressões N+1.

## Clock

`app.core.clock` define `Clock`, `SystemClock` e `FrozenClock`. Produção usa o
calendário local timezone-aware do processo; testes injetam uma data explícita.
A primeira vertical migrada é Proventos, incluindo o limite entre `A_RECEBER` e
`RECEBIDO`. Não use `date.today()` diretamente nessa vertical.

## Configuração

`Settings` rejeita cedo URLs, portas e limites inválidos. Em `production`, são
obrigatórios `APP_BRANCH=stable-15jun`, `APP_COMMIT_SHA` hexadecimal completo e
`REAL_DATASET_REFERENCE` canônica. Mensagens de validação citam apenas o nome do
campo ou a regra, nunca o valor recebido.

Os exemplos `.env.example` e `.env.oci.example` documentam a identidade. O
Compose de produção define `ENVIRONMENT=production`; `APP_ENV` não é contrato
do backend.

## Query budgets

Testes podem usar `tests.query_budget.assert_max_queries(engine, maximum)`. O
contexto conta statements via eventos SQLAlchemy, remove sempre o listener e
falha com `QueryBudgetExceeded` quando o limite é ultrapassado. A leitura
canônica de direitos de Proventos mantém um plano fixo de duas queries: eventos
e movimentos, sem query dentro do loop de eventos.

Validação focada em PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/test_deterministic_runtime_contract.py `
  backend/tests/test_canonical_dividend_entitlement_reader.py -q
```
