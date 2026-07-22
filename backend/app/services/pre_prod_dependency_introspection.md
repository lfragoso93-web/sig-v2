# Introspecção de dependências pré-produção

Este componente é estritamente read-only e transforma foreign keys reais do banco em relações `dependent -> dependency` usadas pelo DAG de planejamento.

## Garantias

- consulta somente metadados do banco;
- não executa limpeza, exportação, seed ou rebuild;
- rejeita referências para tabelas fora do inventário recebido;
- preserva foreign keys autorreferentes como ciclos bloqueantes;
- produz ordem de rebuild com dependências primeiro;
- produz ordem de limpeza como inverso da ordem de rebuild;
- não produz ordens quando existe ciclo.

## Dialetos

- PostgreSQL: consulta `information_schema.table_constraints` e `information_schema.constraint_column_usage` no schema `public`;
- SQLite: suporte exclusivo para testes por meio de `PRAGMA foreign_key_list`.

A integração destes dados no contrato versionado `pre-prod-cleanup-impact` pertence ao bloco seguinte da Issue #185.
