# Estado de implementação — Eventos Corporativos

> Atualizado em 31/07/2026  
> Branch: `stable-15jun`  
> Issue principal: #129  
> Integrações relacionadas: #127, #130 e #226

## Decisão arquitetural vigente

Eventos corporativos são eventos globais associados aos ativos e não devem editar, substituir ou criar transações históricas do usuário. A posição é uma projeção reconstruível formada pela sequência cronológica de transações e eventos reconciliados.

A estratégia original da Issue #129, centrada em HG Brasil, foi superada pela disponibilidade contratual da BRAPI Pro para bonificações e subscrições. Splits e grupamentos permanecem obtidos por fonte corporativa explícita complementar enquanto o contrato real da BRAPI não comprovar esses eventos de forma suficiente.

## Implementado

### Domínio e projeção pura

- motor independente de provedor em `corporate_action_engine.py`;
- tipos canônicos para desdobramento, grupamento, bonificação e subscrição;
- identidade determinística por fonte e conteúdo econômico;
- projeção pura de quantidade, custo total, preço médio e resultado realizado;
- taxas de venda são descontadas do resultado realizado no projetor canônico;
- preservação do custo total em eventos gratuitos;
- subscrição registrada como direito, sem aumento automático da posição;
- transações originais preservadas.

### Coleta e catálogo global

- normalização de `stockDividends` e `subscriptions` da BRAPI Pro;
- normalização de fatores explícitos de split/grupamento do Yahoo;
- persistência idempotente em `corporate_events`;
- payload bruto auditável;
- scheduler limitado à coleta global;
- savepoint por ativo;
- remoção do fluxo legado que aplicava eventos diretamente nas carteiras e criava transações técnicas incompatíveis.

### Integração com posições

- criado projetor cronológico puro em `position_timeline_projection.py`;
- compras, vendas e eventos corporativos são intercalados por data;
- split, grupamento e bonificação transformam somente a quantidade vigente;
- venda posterior usa a quantidade já transformada, reduz custo proporcionalmente e calcula resultado realizado pelo preço médio vigente, líquido das taxas da venda;
- posição zerada antes do evento não recebe transformação;
- recompra posterior não recebe evento retroativo;
- subscrição permanece direito sem aumento automático da quantidade;
- `calc_raw_positions` passou a carregar somente eventos globais de `corporate_events` por adaptador read-only;
- custo total em BRL e custo original em USD continuam preservados;
- nenhuma transação, linha de evento, migration ou schema é alterado durante a projeção.

### Integração com snapshots

- `portfolio_snapshot_service._build_positions_at` deixou de reconstruir posição com regra própria;
- o serviço carrega somente transações da carteira solicitada até `target_date`;
- eventos corporativos são carregados do catálogo global e aplicados pela mesma linha temporal canônica;
- quantidade, custo e resultado realizado do snapshot passam a usar o projetor compartilhado;
- duas carteiras com o mesmo ativo permanecem isoladas pelas transações fornecidas ao adaptador;
- eventos posteriores à data do snapshot não são aplicados;
- métodos internos duplicados de compra e venda foram removidos do caminho ativo de snapshots;
- nenhuma linha persistida de snapshot foi reconstruída automaticamente neste bloco.

### Integração com snapshots por classe

- criado `class_snapshot_position_projection.py` como adaptador puro sobre o projetor canônico;
- `portfolio_class_snapshot_service` deixou de manter estado próprio de compra, venda, custo e realizado;
- eventos corporativos globais são carregados uma única vez por reconstrução e aplicados por ticker;
- transações continuam isoladas pelo `portfolio_id` solicitado;
- cada dia útil projeta quantidade, custo e resultado realizado até a data do snapshot;
- agregação por classe usa somente posições projetadas e não altera valuation, dividendos ou TWR;
- fluxos externos continuam derivados apenas das transações do próprio dia;
- duas carteiras com o mesmo ativo permanecem isoladas pelas transações fornecidas ao adaptador;
- eventos posteriores à data do snapshot não afetam a série histórica;
- a classe duplicada `ClassPositionState` foi removida do caminho ativo.

### Integração com performance legada

- `performance_service` deixou de reconstruir posições diretamente a partir de transações;
- a lista detalhada do endpoint legado passa a consumir `calc_raw_positions`;
- quantidade, custo investido e continuidade pós-evento seguem o mesmo projetor canônico usado por Resumo e Patrimônio;
- os totais consolidados continuam vindo de `get_canonical_portfolio_summary`;
- o formato público do endpoint permanece inalterado;
- fallback de cotação continua usando o preço médio derivado do custo projetado.

### Preparação da rentabilidade realizada

- `snapshot_position_projection.py` passou a expor `project_transaction_timelines`;
- o helper reutiliza a conversão canônica de transações para movimentos;
- linhas temporais encerradas permanecem disponíveis com `realized_pnl` acumulado;
- `project_snapshot_positions` mantém o comportamento anterior e continua retornando somente posições abertas;
- a separação permite migrar Rentabilidade e IRPF sem duplicar regras de quantidade, custo, câmbio ou taxas.

### Proventos relacionados a eventos

- dividendos históricos complementares são normalizados considerando splits e grupamentos posteriores explicitamente publicados;
- o valor original do provedor e o fator aplicado permanecem auditáveis;
- a reconciliação econômica de Proventos continua estrita.

## Parcialmente implementado

### Propagação aos consumidores canônicos

Resumo, Patrimônio, posições atuais, snapshots consolidados, snapshots por classe e performance legada já recebem quantidade e custo projetados. O contrato necessário para resultado realizado de posições abertas e encerradas já está disponível; ainda é necessário conectar os leitores paralelos de Rentabilidade e IRPF.

### Scheduler

A coleta global foi endurecida, mas ainda é necessário confirmar a consolidação completa no scheduler oficial e aposentar qualquer scheduler redundante remanescente.

### Reconciliação entre fontes

A identidade por fonte é determinística, mas ainda falta um estado canônico explícito de reconciliação para divergências econômicas entre provedores.

## Não implementado

- mudança de ticker e aliases históricos;
- conversões, incorporações, fusões e cisões;
- ativo de origem e ativo de destino;
- componentes financeiros e frações;
- fluxo administrativo de revisão, simulação, aprovação e rejeição;
- rollback administrativo de eventos complexos;
- reconstrução seletiva de snapshots por evento;
- integração dedicada com IRPF;
- carga histórica corporativa auditável de 2000 até a data corrente;
- cliente BRAPI v2 unificado com `coverage`, erros tipados, retry e rate limit centralizados.

## Sequência técnica aprovada

1. Conectar o resultado realizado de Rentabilidade ao helper canônico de linhas temporais.
2. Migrar o leitor paralelo de IRPF.
3. Implementar reconciliação explícita entre fontes e estados de conflito/revisão.
4. Construir carga histórica auditável e provar idempotência.
5. Consolidar o scheduler corporativo oficial.
6. Unificar o cliente BRAPI v2 e consultar cobertura antes das coletas.
7. Evoluir para renomes, conversões e eventos complexos.
8. Adicionar administração, simulação e auditoria operacional.

## Invariantes vigentes

- nenhuma transação histórica é criada ou modificada;
- apenas eventos globais com `portfolio_id IS NULL` entram na projeção;
- tipos desconhecidos não são inferidos silenciosamente;
- custo total é preservado em eventos gratuitos;
- taxas de venda reduzem o resultado realizado, sem alterar o custo remanescente além da baixa proporcional;
- subscrição não altera posição sem exercício explícito;
- eventos anteriores a uma recompra não afetam o novo ciclo da posição;
- snapshots são projeções por `portfolio_id` e data, nunca dados globais;
- performance legada consome posições projetadas, mas mantém os totais no resumo canônico;
- posições encerradas não entram em snapshots, mas seu realizado permanece disponível aos consumidores analíticos;
- adaptadores de posição e snapshot são exclusivamente read-only.
