# Decisões de contratos legados — Alembic × ORM (2026-08)

Issue principal: #241.

## Escopo

Este documento registra a decisão provisória sobre `fx_rates` e `goal_allocations`, identificados pelo `alembic check` como tabelas presentes no schema migrado e ausentes do `MetaData` ORM atual.

## Evidência de consumidores

A busca no código atual da `stable-15jun` não encontrou consumidores ativos por nome de tabela, classe ou contrato para:

- `fx_rates`;
- `goal_allocations`.

Essa ausência não autoriza remoção automática. Ela apenas classifica os objetos como contratos migrados sem consumidor ORM comprovado no estado atual.

## `fx_rates`

Estado provisório: **schema legado preservado, consumidor não comprovado**.

Regras:

- não reintroduzir um modelo ORM apenas para silenciar `alembic check`;
- não remover a tabela enquanto o domínio de câmbio e valuation internacional não tiver inventário completo;
- confirmar se alguma rotina SQL, importador, relatório ou histórico depende da tabela;
- qualquer remoção futura exige fixture sintética, contagem antes/depois e coordenação com valuation e ativos internacionais.

## `goal_allocations`

Estado provisório: **schema legado preservado, consumidor não comprovado**.

O modelo atual `Goal` não expõe relacionamento ou coleção para `goal_allocations`. Isso sugere que a alocação detalhada por classe/ativo deixou de fazer parte do contrato ORM atual, mas não prova que os dados sejam descartáveis.

Regras:

- não reintroduzir relacionamento automaticamente;
- não remover a tabela até revisar endpoints, serviços e frontend de metas;
- comparar a capacidade histórica de alocação com `portfolio_class_targets` e com o modelo atual de metas;
- qualquer remoção futura exige fixture sintética com meta e alocações vinculadas.

## Decisão arquitetural

Até nova evidência:

1. ambas as tabelas permanecem no schema migrado;
2. ambas ficam fora do agregador ORM atual;
3. o Alembic não pode autogerar `drop_table` para esses objetos;
4. a convergência será feita por decisão explícita de domínio, nunca por ausência no `MetaData`;
5. nenhuma migration é criada neste bloco.

## Próximos passos

- inventariar SQL bruto e scripts operacionais;
- revisar consumidores de câmbio e metas no frontend e routers;
- criar fixture sintética para cada contrato antes de qualquer alteração destrutiva;
- registrar a decisão final na #241 e nas Issues funcionais correspondentes.
