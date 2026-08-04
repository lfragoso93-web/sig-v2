# Integração frontend da apuração anual canônica de IRPF

## Estado atual

A `IRPFPage.tsx` consome quatro contratos públicos versionados:

```text
GET /portfolios/{portfolio_id}/irpf/{year}/canonical
schema_version = irpf-annual-assessment.v1

GET /portfolios/{portfolio_id}/irpf/{year}/canonical/assets
schema_version = irpf-assets-assessment.v1

GET /portfolios/{portfolio_id}/irpf/{year}/canonical/income
schema_version = irpf-income-assessment.v1

GET /portfolios/{portfolio_id}/irpf/{year}/canonical/capital-gains
schema_version = irpf-capital-gains-assessment.v1
```

Os KPIs fiscais principais usam exclusivamente o contrato anual canônico:

- imposto bruto anual;
- IRRF compensado;
- DARF efetivamente liberada após compensações e mínimo de R$ 10,00;
- prejuízo Day Trade final a compensar.

Bens e Direitos usam exclusivamente o contrato `irpf-assets-assessment.v1`.

Dividendos e JCP usam exclusivamente o contrato `irpf-income-assessment.v1`.

O detalhamento mensal e por venda de Ganhos de Capital usa exclusivamente o contrato `irpf-capital-gains-assessment.v1`.

## Fronteira híbrida temporária

A página ainda carrega o relatório legado somente para habilitar e alimentar:

- arquivos PDF;
- arquivos CSV.

Nenhuma visão da interface usa dados do `IRPFReportOut`.

A fronteira é intencional:

- `useIRPFCanonicalAnnualAssessment` atende os KPIs fiscais principais;
- `useIRPFCanonicalAssetsAssessment` atende Bens e Direitos;
- `useIRPFCanonicalIncomeAssessment` atende Dividendos e JCP;
- `useIRPFCanonicalCapitalGainsAssessment` atende Ganhos de Capital;
- `useIRPFReport` atende somente exportações legadas;
- não existe fallback silencioso dos contratos canônicos para `IRPFReportOut`.

## Tipos monetários

Os envelopes canônicos serializam totais decimais como strings. O cliente mantém esses campos como `string` nos contratos TypeScript e converte para `number` somente na fronteira de apresentação com `formatBRL`.

Os itens detalhados ainda preservam os tipos numéricos dos schemas existentes para manter compatibilidade enquanto os serviços internos são progressivamente normalizados para `Decimal`.

## Refresh

O botão da página foi renomeado para `Recalcular exportações` porque o parâmetro `refresh` pertence somente ao relatório legado persistido.

Os quatro contratos canônicos são read-only e calculados diretamente pelos endpoints dedicados.

## Política de validação do frontend

A integração canônica é validada por:

- ESLint sem warnings;
- `tsc --noEmit`;
- suíte Vitest comportamental existente;
- build de produção com Vite;
- testes backend dos endpoints e serviços canônicos.

Não são mantidos testes que leem o próprio código-fonte para procurar strings de implementação. Essas suítes eram frágeis no ambiente Vitest e não adicionavam cobertura comportamental relevante.

## Próximos cortes

1. criar exportações PDF/CSV baseadas nos contratos canônicos;
2. remover o carregamento de `IRPFReportOut` da página;
3. retirar o motor e a persistência fiscal legados quando não houver consumidores;
4. concluir a validação operacional com carteira representativa quando houver dados disponíveis.
