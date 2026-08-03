# Fronteiras arquiteturais — Dados globais de ativos e estado de carteira

> Atualizado em 31/07/2026  
> Branch: `stable-15jun`  
> Issue principal: #129

## Objetivo

Definir de forma explícita quais dados pertencem ao domínio global dos ativos e quais estados pertencem às carteiras dos usuários. Esta separação é obrigatória para evitar duplicação de dados, vazamento entre carteiras, divergência de cálculos e materializações incompatíveis com a arquitetura DB-first do SGI v2.

## Princípio central

Dados econômicos e cadastrais do ativo são globais. Estado financeiro de carteira é sempre derivado exclusivamente das transações registradas naquela carteira, combinado com os dados globais aplicáveis ao ativo e à data de cálculo.

Nenhuma carteira cria, possui ou duplica o ativo, o preço, o provento ou o evento corporativo. A carteira apenas referencia esses dados para projetar sua própria posição.

## Domínio global do ativo

Pertencem ao domínio global:

- `assets` e identidade econômica do ativo;
- ticker atual, aliases e histórico de ticker;
- classe, moeda, setor e metadados cadastrais;
- preços atuais e históricos;
- dados de mercado e fundamentos;
- proventos globais em `asset_dividends`;
- eventos corporativos globais em `corporate_events`;
- dados brutos e normalizados dos provedores;
- regras de reconciliação e proveniência;
- cobertura, status e metadados de integração.

### Identidade global mínima

Enquanto a migração para vínculo obrigatório por `asset_id` não estiver concluída, a identidade global mínima é:

```text
(ticker, asset_type)
```

A identidade alvo é:

```text
asset_id
```

Ticker não deve ser tratado como identidade econômica permanente, pois pode mudar em renomes, conversões e reorganizações societárias.

## Domínio da carteira

Pertencem ao domínio da carteira:

- `portfolios`;
- `transactions`;
- quantidade projetada;
- custo total e preço médio;
- resultado realizado e não realizado;
- direitos de proventos derivados;
- posições consolidadas;
- snapshots históricos;
- patrimônio;
- rentabilidade e TWR;
- metas, alocações e indicadores específicos da carteira;
- caches cujo conteúdo dependa de `portfolio_id`.

### Identidade mínima do estado da carteira

Enquanto `transactions` não possuir vínculo obrigatório por `asset_id`, a identidade mínima de uma posição derivada é:

```text
(portfolio_id, ticker, asset_type)
```

A identidade alvo é:

```text
(portfolio_id, asset_id)
```

Nenhum cálculo de posição pode usar apenas ticker como chave quando houver risco de colisão entre classes ou histórico de renome.

## Projeção canônica por carteira e data

Toda posição deve ser reconstruída com a mesma regra:

```text
transações da carteira até a data
+ eventos globais do ativo até a data
+ preços globais aplicáveis à data
= estado derivado da carteira
```

Para cada `portfolio_id` e `target_date`, o serviço canônico deve:

1. carregar somente transações da carteira;
2. resolver os ativos envolvidos;
3. carregar eventos globais aplicáveis;
4. intercalar transações e eventos em ordem cronológica;
5. calcular quantidade, custo e resultado realizado;
6. buscar preços globais da data;
7. calcular patrimônio e métricas;
8. persistir apenas o snapshot da carteira quando o consumidor exigir materialização.

## Regras para eventos corporativos

Eventos corporativos são globais e nunca devem ser duplicados por carteira.

O efeito é calculado individualmente por carteira:

- posição existente na data recebe o evento;
- posição zerada antes da data não recebe o evento;
- recompra posterior não recebe evento retroativo;
- split, grupamento e bonificação alteram quantidade e preservam custo total;
- subscrição cria direito, mas não altera quantidade sem exercício explícito;
- transações históricas permanecem imutáveis.

`corporate_events.portfolio_id` é legado arquitetural. Novos eventos devem permanecer globais com `portfolio_id IS NULL`. A remoção física da coluna exige inventário, migration separada e prova de que não existem consumidores válidos dependentes dela.

## Regras para proventos

O evento de provento é global. O direito é derivado por carteira.

- Data Com, Data Ex, Data de Pagamento e valor por unidade pertencem ao ativo;
- quantidade elegível pertence à projeção histórica da carteira;
- duas carteiras podem ter direitos diferentes sobre o mesmo evento;
- nenhuma linha global deve ser copiada para cada carteira;
- direitos derivados devem permanecer read-only ou reconstruíveis.

## Regras para snapshots

Snapshots pertencem exclusivamente à carteira.

Cada snapshot deve representar:

> o estado daquela carteira na data, considerando somente suas transações e os dados globais aplicáveis aos ativos envolvidos.

Um snapshot não é fonte primária de verdade. Ele é uma materialização reconstruível para desempenho e histórico.

### Invalidação obrigatória

Snapshots afetados devem ser invalidados ou reconstruídos quando ocorrer:

- criação, edição ou exclusão de transação;
- inclusão ou correção retroativa de evento corporativo;
- mudança de identidade ou ticker;
- correção de preço histórico;
- correção de câmbio histórico;
- alteração de regra canônica de projeção.

A invalidação deve ser limitada às carteiras e datas afetadas.

## Materialização de posições

`portfolio_positions` pode existir apenas como cache/materialização reconstruível.

Não pode ser fonte primária de verdade nem ser atualizado somente por transações, pois eventos corporativos globais também alteram quantidade e preço médio.

Enquanto não houver contrato completo de invalidação e reconstrução, consumidores canônicos devem preferir projeção sob consulta.

## Caches

Caches devem respeitar a natureza do dado:

- cache de preço, logo, fundamento e evento: global por ativo;
- cache de posição, resumo, patrimônio e rentabilidade: obrigatoriamente por `portfolio_id`;
- nenhuma chave de cache de estado financeiro pode omitir a carteira;
- correções globais retroativas devem invalidar caches das carteiras afetadas.

## Dependências permitidas

Fluxo permitido:

```text
catálogo global do ativo
        ↓
projetor canônico por carteira e data
        ↓
posições / snapshots / patrimônio / rentabilidade / IRPF
```

Fluxos proibidos:

- evento global gravando transação técnica na carteira;
- provento global duplicado em cada carteira;
- snapshot global compartilhado entre carteiras;
- posição de uma carteira influenciada por transações de outra;
- cálculo de carteira sem filtro obrigatório de `portfolio_id`;
- ticker isolado como identidade definitiva em estado de carteira.

## Inconsistências atuais conhecidas

1. `CorporateEvent` ainda possui `portfolio_id` e relacionamento com `Portfolio`.
2. `PortfolioPosition` é descrita como atualizada a cada transação, sem contrato explícito de eventos globais.
3. `portfolio_snapshot_service._build_positions_at` ainda reconstrói posição apenas por transações.
4. Leitores paralelos de valuation, rentabilidade e IRPF precisam ser inventariados para detectar reconstruções próprias.
5. `transactions` ainda não possui vínculo canônico obrigatório por `asset_id`.
6. Parte dos caches e invalidadores ainda precisa ser revisada diante de eventos retroativos.

## Plano incremental aprovado

1. Formalizar estas fronteiras e protegê-las por documentação viva.
2. Migrar `portfolio_snapshot_service._build_positions_at` para o projetor canônico por carteira e data.
3. Inventariar e migrar valuation, rentabilidade, TWR e IRPF.
4. Definir invalidação seletiva por evento global retroativo.
5. Auditar `portfolio_positions` e decidir entre remoção, reconstrução ou contrato explícito de materialização.
6. Migrar transações para vínculo por `asset_id` sem perder histórico.
7. Remover `corporate_events.portfolio_id` em migration própria após prova de ausência de dependências.
8. Adicionar regressões estruturais contra mistura entre domínio global e carteira.

## Invariantes obrigatórios

- ativos e eventos são globais;
- transações e snapshots são isolados por carteira;
- nenhuma transação histórica é criada ou alterada por evento global;
- posição é derivada de transações da carteira e eventos globais aplicáveis;
- toda consulta de estado financeiro exige `portfolio_id`;
- materializações são reconstruíveis e nunca fonte primária;
- correções globais retroativas propagam invalidação somente às carteiras afetadas;
- documentação, Issues e código devem refletir a mesma fronteira arquitetural.
