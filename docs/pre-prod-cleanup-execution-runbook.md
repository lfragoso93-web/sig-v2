# Runbook — limpeza controlada pré-produção em ambiente isolado

## Estado

Este documento define o próximo bloco da Issue #158 após a validação real da cadeia `export -> cleanup impact -> cleanup plan-only` concluída na Issue #195.

A limpeza da base real continua proibida. O primeiro alvo obrigatório é um banco PostgreSQL isolado, restaurado a partir do backup validado `pre-prod-backup.v3`.

## Objetivo do bloco

Implementar e validar uma execução controlada que:

1. consuma somente um `cleanup/plan.json` previamente aprovado;
2. confirme novamente identidade, checksums, contagens e ordem da DAG;
3. recuse o banco de origem e qualquer destino não explicitamente isolado;
4. execute a limpeza dentro de uma única transação;
5. faça rollback integral diante de qualquer divergência;
6. publique relatório auditável sem sobrescrever artefatos existentes.

## Gates obrigatórios antes de qualquer SQL destrutivo

A execução deve abortar antes da primeira escrita quando qualquer condição abaixo falhar:

- branch diferente de `stable-15jun`;
- SHA Git diferente do registrado no plano;
- `run_id` ausente, reutilizado ou incompatível;
- schema diferente de `pre-prod-cleanup-execution.v1`;
- `mode` diferente de `plan`;
- blockers presentes;
- ciclos presentes no plano de dependências;
- checksums divergentes para `cleanup-impact.json`, manifesto ou CSVs;
- conjunto de tabelas exportadas diferente das tabelas `export_before_cleanup`;
- contagem atual de qualquer tabela diferente de `expected_rows_before`;
- URL do banco igual à origem;
- banco de destino sem marcador explícito de isolamento;
- conexão sem transação controlada;
- processos de coleta, seed ou rebuild ativos no destino.

## Confirmação operacional

A futura CLI de execução deve exigir confirmação explícita composta, não apenas um booleano genérico. A confirmação deve vincular:

- `run_id`;
- nome do banco isolado;
- SHA completo;
- checksum do plano;
- literal inequívoco de autorização para o ambiente isolado.

A confirmação não pode ser persistida como padrão, reutilizada por outra execução nem lida de variável de ambiente genérica.

## Estratégia transacional

A implementação deve:

1. abrir uma única transação no banco isolado;
2. adquirir lock operacional para impedir concorrência;
3. validar todas as contagens antes de qualquer limpeza;
4. limpar as tabelas exatamente na ordem registrada no plano;
5. validar contagem zero após cada operação;
6. manter tabelas preservadas fora do conjunto de escrita;
7. gerar o relatório ainda dentro do contexto controlado;
8. efetivar `COMMIT` somente após todas as validações;
9. executar `ROLLBACK` em qualquer exceção ou divergência.

Não será permitido `DROP DATABASE`, `DROP TABLE`, alteração de schema ou execução parcial fora da transação.

## Tabelas do plano validado

Ordem aprovada pela execução real `20260723-095541`:

1. `transactions`
2. `portfolio_snapshots`
3. `portfolio_positions`
4. `portfolio_class_snapshots`
5. `fixed_income_investments`
6. `dividends`
7. `corporate_events`
8. `rate_history`
9. `fx_rates`
10. `asset_prices`
11. `asset_dividends`
12. `asset_aliases`
13. `assets`

A implementação não deve manter uma segunda lista codificada. A única ordem válida deve vir do plano aprovado e ser novamente validada contra o contrato canônico.

## Relatório de execução

O artefato deve ser publicado em:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup/execution.json
```

Conteúdo mínimo:

- schema version próprio;
- `run_id`, branch, SHA e banco de destino redigido;
- checksum do plano consumido;
- timestamps de início e término;
- contagens antes e depois por tabela;
- ordem efetivamente executada;
- número de escritas;
- estado final `committed` ou `rolled_back`;
- motivo de aborto, quando aplicável;
- confirmação de que nenhuma tabela preservada foi alterada;
- confirmação de que nenhum rebuild foi iniciado.

A publicação deve ser atômica e sem sobrescrita.

O publicador de sucesso foi implementado no Bloco C1. Ele grava UTF-8 em arquivo temporário no mesmo diretório, sincroniza o conteúdo, cria o destino por hard link exclusivo e sincroniza o diretório final. URL, usuário e senha não entram no artefato; somente o rótulo redigido `host:port/database` é persistido.

## Sequência de implementação

### Bloco A — contrato e validações puras

- contrato versionado do relatório;
- validação da confirmação composta;
- validação do alvo isolado;
- validação de plano, identidade e checksum;
- testes unitários sem banco.

### Bloco B — executor transacional

- lock operacional;
- validação de contagens;
- limpeza parametrizada pela ordem do plano;
- rollback integral;
- testes com banco isolado de teste.

### Bloco C — CLI e artefato

- [x] publicador atômico e sem sobrescrita para `cleanup/execution.json`;
- [x] relatório de sucesso redigido, UTF-8 e reconciliado;
- [ ] validar localmente os testes do publicador;
- [ ] CLI explícita para ambiente isolado;
- [ ] exit codes distintos;
- [ ] relatório de rollback/aborto sem expor credenciais.

### Bloco D — ensaio real isolado

- restaurar backup v3 em banco descartável;
- executar a limpeza controlada;
- reconciliar contagens e tabelas preservadas;
- descartar o banco após coleta das evidências.

Somente após o Bloco D reconciliado poderá ser criada uma etapa separada para avaliar execução na base pré-produção real.

## Operações proibidas neste estágio

- executar a limpeza na base real;
- reutilizar o `run_id` validado;
- editar manualmente o plano ou os CSVs;
- ignorar divergências de contagem;
- usar `CASCADE` para contornar uma DAG incorreta;
- iniciar seed, coleta, importação ou rebuild dentro do mesmo bloco;
- alterar tabelas preservadas;
- promover automaticamente a autorização do ambiente isolado para pré-produção.

## Critério de conclusão deste bloco documental

- Issue dedicada criada e vinculada à #158;
- arquitetura e gates documentados;
- nenhuma escrita em banco executada;
- Bloco C1 implementado sem integrar a CLI ao banco real ou isolado;
- validação local do Bloco C1 ainda pendente.