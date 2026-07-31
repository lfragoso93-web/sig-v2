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
- projeção pura de quantidade, custo total e preço médio;
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
- venda posterior usa a quantidade já transformada e reduz o custo proporcionalmente;
- posição zerada antes do evento não recebe transformação;
- recompra posterior não recebe evento retroativo;
- subscrição permanece direito sem aumento automático da quantidade;
- `calc_raw_positions` passou a carregar somente eventos globais de `corporate_events` por adaptador read-only;
- custo total em BRL e custo original em USD continuam preservados;
- nenhuma transação, linha de evento, migration ou schema é alterado durante a projeção.

### Proventos relacionados a eventos

- dividendos históricos complementares são normalizados considerando splits e grupamentos posteriores explicitamente publicados;
- o valor original do provedor e o fator aplicado permanecem auditáveis;
- a reconciliação econômica de Proventos continua estrita.

## Parcialmente implementado

### Propagação aos consumidores canônicos

Resumo, Patrimônio e posições que consomem `calc_raw_positions` já recebem a quantidade projetada. Ainda é necessário inventariar os leitores paralelos de valuation, snapshots, rentabilidade e IRPF para garantir que nenhum deles reconstrua posição somente a partir de transações.

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

1. Inventariar e migrar leitores paralelos de posição usados por valuation, rentabilidade, snapshots e IRPF.
2. Implementar reconciliação explícita entre fontes e estados de conflito/revisão.
3. Construir carga histórica auditável e provar idempotência.
4. Consolidar o scheduler corporativo oficial.
5. Unificar o cliente BRAPI v2 e consultar cobertura antes das coletas.
6. Evoluir para renomes, conversões e eventos complexos.
7. Adicionar administração, simulação e auditoria operacional.

## Invariantes vigentes

- nenhuma transação histórica é criada ou modificada;
- apenas eventos globais com `portfolio_id IS NULL` entram na projeção;
- tipos desconhecidos não são inferidos silenciosamente;
- custo total é preservado em eventos gratuitos;
- subscrição não altera posição sem exercício explícito;
- eventos anteriores a uma recompra não afetam o novo ciclo da posição;
- o adaptador de posição é exclusivamente read-only.
