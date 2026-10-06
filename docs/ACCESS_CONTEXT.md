# Access Context e autorização por carteira

> Estado em 06/10/2026: contrato canônico introduzido na vertical de dividendos.

## Regra

Todo novo acesso a dados sensíveis por carteira deve receber um
`PortfolioAccessContext`. IDs vindos de path, header ou body não constituem
autorização. O controller traduz a identidade autenticada para o contexto; o
service declara a permissão necessária; o repository combina escopo e
ownership na consulta ao banco.

Falhas de carteira inexistente, pertencente a outro usuário ou sem permissão
usam a mesma resposta pública. Isso evita confirmar a existência de carteiras
de terceiros.

## Contextos de usuário e sistema

`PortfolioAccessContext.for_user(...)` exige `user_id`, `portfolio_id` e um
conjunto não vazio de permissões. `for_system(...)` não aceita `user_id` e exige
um `purpose` explícito. Jobs, CLIs e rotinas administrativas não podem obter
acesso sistêmico por omissão, booleano de bypass ou usuário artificial.

```python
access = PortfolioAccessContext.for_user(
    user_id=current_user.id,
    portfolio_id=portfolio_id,
    permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
)
```

Uma rotina sistêmica read-only deve declarar sua finalidade:

```python
access = PortfolioAccessContext.for_system(
    portfolio_id=portfolio_id,
    permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
    purpose="certification-readonly-reconciliation",
)
```

Criar um contexto não concede acesso automaticamente. O repository ainda deve
chamar `access.require(...)` e aplicar o escopo de ownership correspondente.

## Primeira vertical migrada

`GET /api/v1/portfolios/{portfolio_id}/dividends` cobre o fluxo completo:

```text
current_user autenticado
        -> PortfolioAccessContext.for_user
        -> dividend_service.list_dividends
        -> portfolio_access_repository.get_accessible_portfolio
        -> leitura financeira somente após ownership + permissão
```

A CLI read-only de reconciliação da carteira sintética também constrói um
contexto de usuário a partir da identidade certificada. Ela não usa bypass
sistêmico implícito.

## Inventário inicial de superfícies sensíveis

| Superfície | Estado observado | Prioridade de migração |
| --- | --- | --- |
| Dividendos | contexto completo em controller/service/repository | concluída neste bloco |
| Transações | ownership local no router; IDs livres abaixo da borda | alta |
| IRPF | ownership local no router; serviços recebem `portfolio_id` | alta |
| Proventos | ownership local no router; serviços recebem `portfolio_id` | alta |
| Rentabilidade | ownership local no router; serviços recebem IDs | média |
| Posições/resumo | validações duplicadas entre router e service | média |
| Metas e class targets | ownership local no router | média |
| CSV/importações | validação própria por `portfolio_id` + `user_id` | alta em writes |
| Rebuilds, seeds e schedulers | seleção sistêmica direta de carteiras | exigir `for_system` antes de migrar |

O inventário indica risco estrutural, não uma vulnerabilidade confirmada em
cada rota. As migrações seguintes devem permanecer verticais e revisáveis.

## Testes obrigatórios

- acesso do proprietário passa somente com a permissão exigida;
- carteira de outro usuário falha antes da leitura sensível;
- permissão ausente falha antes de consultar o banco;
- contexto sistêmico exige finalidade explícita e nunca impersona usuário;
- mensagens públicas não distinguem ausência de cross-ownership.

Validação focada no PowerShell:

```powershell
cd backend
$env:ENVIRONMENT = "development"
..\.venv\Scripts\python.exe -m pytest tests/test_portfolio_access_context.py tests/test_dividend_service_on_demand.py tests/test_portfolio_certification_reconcile_income.py -q -p no:cacheprovider
```
