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

## Exportações canônicas

Os endpoints PDF e CSV compõem seus dados diretamente a partir dos serviços canônicos read-only:

- apuração anual;
- Bens e Direitos;
- Ganhos de Capital;
- dividendos e JCP.

A composição é feita por `IrpfCanonicalExport` e `build_irpf_canonical_export`.

Os endpoints preservam:

- URLs públicas existentes;
- nomes de arquivo;
- MIME types;
- seções funcionais dos relatórios.

Não há fallback para `IRPFReport`, `IRPFReportOut`, `generate_irpf_report` ou persistência fiscal legada nas exportações.

## Fronteira frontend

A página não carrega mais `useIRPFReport` e não usa o parâmetro legado `refresh`.

A fronteira atual é integralmente canônica:

- `useIRPFCanonicalAnnualAssessment` atende os KPIs fiscais principais;
- `useIRPFCanonicalAssetsAssessment` atende Bens e Direitos;
- `useIRPFCanonicalIncomeAssessment` atende Dividendos e JCP;
- `useIRPFCanonicalCapitalGainsAssessment` atende Ganhos de Capital;
- PDF e CSV são solicitados diretamente aos endpoints canônicos de exportação.

## Tipos monetários

Os envelopes canônicos serializam totais decimais como strings. O cliente mantém esses campos como `string` nos contratos TypeScript e converte para `number` somente na fronteira de apresentação com `formatBRL`.

Os itens detalhados ainda preservam os tipos numéricos dos schemas existentes para manter compatibilidade enquanto os serviços internos são progressivamente normalizados para `Decimal`.

## Política de validação

A integração canônica é validada por:

- Ruff;
- ESLint sem warnings;
- `tsc --noEmit`;
- suíte Vitest comportamental existente;
- build de produção com Vite;
- testes backend dos endpoints, composição e serviços canônicos;
- suíte backend completa.

Não são mantidos testes que leem o próprio código-fonte para procurar strings de implementação. Essas suítes eram frágeis no ambiente Vitest e não adicionavam cobertura comportamental relevante.

## Próximos cortes

1. executar auditoria final de consumidores e artefatos legados;
2. validar PDF/CSV com carteira representativa quando houver dados disponíveis;
3. sincronizar README, ROADMAP e CHANGELOG no bloco estrutural final;
4. abrir a PR de `stable-15jun` para `main`.
