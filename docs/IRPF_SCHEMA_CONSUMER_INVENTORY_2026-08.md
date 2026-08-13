# Inventário de consumidores do schema IRPF — agosto de 2026

## Escopo

Este documento registra a decisão arquitetural provisória para os contratos:

- `irpf_reports` / `IRPFReport`;
- `irpf_records`;
- `irpf_losses`.

A análise é coordenada com a Issue #56, que já concluiu o módulo funcional canônico de IRPF.

## Evidência funcional atual

A Issue #56 registra que o motor canônico de IRPF é read-only e expõe contratos anuais versionados para apuração, Bens e Direitos, Rendimentos, Ganhos e exportação. A tela principal, PDF e CSV não dependem de `IRPFReport`, `IRPFReportOut`, `generate_irpf_report` ou persistência fiscal legada.

O arquivo `app/services/irpf_service.py` preserva apenas uma fachada Python histórica em memória. Essa fachada adapta `IRPFReportOut` para `IrpfCanonicalExport`, sem consultar banco e sem ler `IRPFReport`.

## `IRPFReport` / `irpf_reports`

### Consumidores encontrados

- import no agregador `app.models`;
- relacionamento `Portfolio.irpf_reports`;
- referência de tipagem em `Portfolio`.

### Consumidores não encontrados

- routers públicos canônicos;
- serviços canônicos de apuração;
- exportadores PDF/CSV canônicos;
- frontend atual;
- consultas, inserts, updates ou deletes no runtime.

### Classificação

`IRPFReport` é um modelo ORM órfão e não migrado. Sua presença no `MetaData` faz o Alembic propor a criação de `irpf_reports`, apesar de o fluxo canônico não precisar de persistência anual.

Decisão recomendada: remover o modelo e o relacionamento ORM em commits pequenos, sem criar a tabela.

## `irpf_records` e `irpf_losses`

### Estado observado

As tabelas existem na cadeia de migrations e possuem granularidade mensal por usuário, mercado e período. Não há modelos ORM ativos nem consumidores runtime comprovados no fluxo canônico atual.

### Risco de remoção

A ausência de consumidor atual não autoriza `drop_table`. Esses contratos preservam granularidade mensal e prejuízos segregados que não devem ser descartados sem:

1. fixture sintética representativa;
2. inventário de dados existentes;
3. decisão explícita sobre compatibilidade histórica;
4. migration destrutiva isolada e reversível.

### Classificação

- `irpf_records`: schema legado preservado, decisão destrutiva pendente;
- `irpf_losses`: schema legado preservado, decisão destrutiva pendente.

## Decisão por contrato

| Contrato | Classificação | Ação imediata |
|---|---|---|
| `IRPFReport` / `irpf_reports` | modelo ORM órfão não migrado | remover do ORM; não criar tabela |
| `irpf_records` | tabela migrada legada sem consumidor comprovado | preservar até fixture e decisão explícita |
| `irpf_losses` | tabela migrada legada sem consumidor comprovado | preservar até fixture e decisão explícita |

## Restrições

- não gerar migration automática para `irpf_reports`;
- não remover `irpf_records` ou `irpf_losses` apenas para silenciar `alembic check`;
- manter a decisão coordenada entre as Issues #56 e #241;
- executar um contrato por commit;
- não acessar dados reais durante este macrobloco.
