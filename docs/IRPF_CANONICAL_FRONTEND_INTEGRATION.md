# Integração frontend da apuração anual canônica de IRPF

## Estado atual

A `IRPFPage.tsx` passou a consumir o contrato público versionado:

```text
GET /portfolios/{portfolio_id}/irpf/{year}/canonical
schema_version = irpf-annual-assessment.v1
```

Os KPIs fiscais principais usam exclusivamente esse contrato:

- imposto bruto anual;
- IRRF compensado;
- DARF efetivamente liberada após compensações e mínimo de R$ 10,00;
- prejuízo Day Trade final a compensar.

## Fronteira híbrida temporária

O contrato canônico ainda não expõe:

- Bens e Direitos;
- dividendos;
- JCP;
- detalhamento legado de vendas;
- arquivos PDF e CSV.

Por isso, essas partes permanecem temporariamente no contrato legado `IRPFReportOut`.

A fronteira é intencional:

- `useIRPFCanonicalAnnualAssessment` atende os KPIs fiscais principais;
- `useIRPFReport` atende apenas dados complementares e downloads legados;
- não existe fallback silencioso dos KPIs canônicos para o relatório legado.

## Tipos monetários

O endpoint serializa valores fiscais decimais como strings. O cliente mantém esses campos como `string` no contrato TypeScript e converte para `number` somente na fronteira de apresentação com `formatBRL`.

Essa decisão evita representar o contrato HTTP como se o backend tivesse enviado números binários de ponto flutuante.

## Refresh

O botão da página foi renomeado para `Recalcular complementos` porque o parâmetro `refresh` pertence somente ao relatório legado persistido.

A apuração canônica é read-only e calculada diretamente pelo endpoint `/canonical`.

## Política de validação do frontend

A integração canônica é validada por:

- ESLint sem warnings;
- `tsc --noEmit`;
- suíte Vitest comportamental existente;
- build de produção com Vite;
- testes backend do endpoint, serviço e mapper canônicos.

Não são mantidos testes que leem o próprio código-fonte para procurar strings de implementação. Essas suítes eram frágeis no ambiente Vitest e não adicionavam cobertura comportamental relevante.

## Próximos cortes

1. adicionar ao contrato canônico os dados necessários para Bens e Direitos e rendimentos, ou criar contratos canônicos dedicados;
2. migrar as abas complementares;
3. criar exportações PDF/CSV baseadas na apuração canônica;
4. remover o consumo de `IRPFReportOut` da página;
5. retirar o motor e a persistência fiscal legados quando não houver consumidores.
