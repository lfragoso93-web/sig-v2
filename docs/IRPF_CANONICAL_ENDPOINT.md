# Endpoint canônico anual de IRPF

## Rota

`GET /{portfolio_id}/irpf/{year}/canonical`

## Objetivo

Expor em modo read-only o contrato versionado `irpf-annual-assessment.v1` para a
carteira autenticada, reutilizando o serviço canônico
`build_irpf_annual_assessment`.

## Autorização e isolamento

Antes da apuração, o router executa `_get_portfolio`, que exige simultaneamente:

- `Portfolio.id == portfolio_id`;
- `Portfolio.user_id == current_user.id`.

Carteira inexistente ou pertencente a outro usuário retorna `404` e o serviço
canônico não é executado.

## Resposta

O schema HTTP `IrpfAnnualAssessmentOut` preserva valores fiscais como `Decimal`
e contém:

- `schema_version`;
- carteira e ano-calendário;
- competências mensais;
- imposto bruto e líquido por modalidade;
- IRRF utilizado;
- DARF liberada;
- saldo acumulado abaixo do mínimo;
- prejuízo Day Trade e saldos finais de IRRF;
- totais anuais.

## Fronteiras arquiteturais

O endpoint:

- não consulta `IRPFReport`;
- não chama `generate_irpf_report`;
- não chama `calc_ganhos_capital`;
- não persiste relatórios ou saldos;
- não possui fallback para o motor legado;
- não altera os endpoints legados existentes;
- não migra automaticamente o frontend.

## Testes protegidos

- autorização por carteira antes do cálculo;
- `404` para carteira de outro usuário ou inexistente;
- ausência de execução do serviço quando não autorizado;
- preservação do `schema_version`;
- propagação de ano fiscal inválido sem fallback legado;
- teste estrutural impedindo dependência do motor legado.
