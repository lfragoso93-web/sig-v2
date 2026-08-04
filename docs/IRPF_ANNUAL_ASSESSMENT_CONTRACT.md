# Contrato interno da apuração anual canônica de IRPF

## Objetivo

Este documento descreve o contrato interno versionado
`irpf-annual-assessment.v1`, criado na Issue #56 para desacoplar a apuração
operacional canônica dos futuros consumidores de API, relatórios e frontend.

## Componentes

- `irpf_annual_assessment_contract.py`: DTOs versionados e serialização interna;
- `irpf_annual_assessment_contract_mapper.py`: projeção pura da apuração anual
  integrada para o contrato;
- `test_irpf_annual_assessment_contract_mapper.py`: proteção da versão, ordem,
  consolidação mensal e totais.

## Conteúdo mensal

Cada competência expõe:

- imposto bruto Swing;
- IRRF Swing efetivamente utilizado;
- imposto líquido Swing;
- imposto bruto Day Trade;
- IRRF Day Trade efetivamente utilizado;
- imposto líquido Day Trade;
- imposto líquido total;
- DARF liberada para pagamento;
- saldo acumulado abaixo do mínimo.

## Conteúdo anual

O contrato expõe:

- `schema_version`;
- carteira e ano-calendário;
- competências ordenadas;
- imposto bruto total;
- IRRF total efetivamente compensado;
- imposto líquido total;
- total liberado para pagamento;
- saldo acumulado final;
- saldos finais de IRRF comum e Day Trade;
- prejuízo Day Trade final a compensar.

## Decisões arquiteturais

- o contrato é interno e read-only;
- o contrato não consulta banco de dados;
- o mapper não recalcula posição, custo, PnL, prejuízos, IRRF ou DARF;
- `Decimal` é preservado na serialização interna;
- não há Pydantic, endpoint ou schema HTTP neste corte;
- nenhuma persistência ou consumidor legado foi alterado.

## Versionamento

A versão inicial é:

```text
irpf-annual-assessment.v1
```

Mudanças incompatíveis exigem nova versão. Campos novos compatíveis podem ser
adicionados somente após revisão dos consumidores e testes contratuais.

## Próximos consumidores permitidos

O contrato pode servir futuramente como fonte para:

- schema de API pública;
- relatório mensal e anual;
- exportação CSV ou PDF;
- frontend de IRPF;
- comparação de transição com o runtime legado.

Esses consumidores não fazem parte deste bloco.
