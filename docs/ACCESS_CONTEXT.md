# Access Context e autorização por carteira

> Atualizado em 03/11/2026: edição/exclusão de transações, IRPF, Proventos,
> Rentabilidade e Posições/resumo validam ownership e permissão no repositório por contexto explícito.

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

`principal_kind` deve ser um membro tipado de `AccessPrincipalKind`; strings
ou valores desconhecidos sao rejeitados na construcao e pelo repository,
antes de qualquer consulta sem filtro de proprietÃ¡rio.

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
| Transações (criação/CSV) | escritor canônico exige `write:portfolio_transactions` e valida ownership no repository | concluída neste bloco |
| Transações (edição/exclusão) | consulta no repositório vincula transação, carteira, ownership e `write:portfolio_transactions`; ausência e falta de acesso retornam a mesma resposta | concluída neste bloco |
| IRPF | endpoints constroem contexto de usuário; serviços de relatório, apuração, exportação e seções validam ownership e `read:portfolio_irpf` no repositório; CLI usa contexto sistêmico com finalidade | concluída neste bloco |
| Proventos | endpoints constroem contexto de usuário; summary/lista/histórico/distribuição validam ownership e `read:portfolio_proventos` no repositório; helpers de projeção internos recebem o ID já autorizado | concluída neste bloco |
| Rentabilidade (página e legado) | 12 endpoints constroem contexto; entrypoints de serviço validam ownership e `read:portfolio_rentabilidade` ou `read:portfolio_performance` no repositório antes de ler snapshots, posições ou benchmarks | concluída neste bloco |
| Posições/resumo | endpoints legado, canônico e exportação constroem contexto e validam ownership + `read:portfolio_positions` no repositório | concluída neste bloco |
| Metas financeiras | rotas constroem contexto; serviços validam ownership e `read:portfolio_goals` ou `write:portfolio_goals` antes do CRUD | concluída neste bloco |
| Class targets | rotas constroem contexto; serviços validam ownership e `read:portfolio_class_targets` ou `write:portfolio_class_targets` antes de listar ou alterar | concluída neste bloco |
| CSV/importações | writer recebe contexto do usuário; carteira ausente e sem acesso têm a mesma resposta | concluída neste bloco |
| Manutenção TWR agendada e rebuild completo | contexto `for_system` com finalidade e permissão `maintain:portfolio_snapshots`, validado no repositório antes da leitura/reconstrução | concluída neste bloco |
| Seeds de transação sintética | `seed_transactions` valida a carteira existente com contexto sistêmico e permissão explícita antes da leitura do estado; todas as gravações usam o escritor canônico; ticker do Tesouro sintético só permanece exato quando confirmado pelo catálogo | concluída neste bloco |
| Ciclo local de certificação de snapshots sintéticos | valida a carteira com `maintain:portfolio_snapshots` e finalidade explícita antes de ler ou invalidar snapshots | concluída neste bloco |
| CLI de reconciliação sintética | valida `read:portfolio_positions` e `read:portfolio_performance` no repositório após confirmar a identidade proprietária e antes das leituras financeiras | concluída neste bloco |
| CLI de certificação IRPF sintético | valida `read:portfolio_irpf` pela fachada de acesso antes de ler baixas e executar a apuração fiscal | concluída neste bloco |
| Outros rebuilds completos e seeds | avaliar cada fluxo sistêmico restante separadamente, mantendo os contratos de propriedade sintética | migrar em blocos separados |

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
