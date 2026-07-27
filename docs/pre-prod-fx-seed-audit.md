# Auditoria arquitetural — seed isolado de câmbio

## Contexto

Este documento registra a auditoria da Issue #217 antes da implementação do seed operacional de câmbio. O estágio deve permanecer isolado de benchmarks, B3, Tesouro, proventos, importação CSV, posições, snapshots e `full_market_rebuild`.

## Correção do inventário

A busca indexada inicial não localizou a implementação existente. A varredura local completa, excluindo `__pycache__` e arquivos `.pyc`, confirmou que o SGI v2 já possui infraestrutura cambial dedicada. Portanto, a hipótese anterior de criar uma nova tabela `fx_rates` foi descartada.

## Arquitetura existente confirmada

### Persistência

Arquivo: `backend/app/models/fx_rate.py`

- tabela existente: `fx_rates`;
- campos: `pair`, `rate_date`, `rate`, `created_at`;
- unicidade: `uq_fx_rates_pair_date` em `pair + rate_date`;
- sem vínculo com `assets` ou `asset_prices`;
- persistência adequada para o primeiro estágio `USD-BRL`.

A tabela é canônica para taxa cambial diária e não deve ser substituída por `asset_prices`.

### Fonte oficial

Arquivo: `backend/app/integrations/bcb.py`

- integração existente com a API PTAX do Banco Central;
- `fetch_usd_brl_period()` para histórico;
- `fetch_usd_brl_day()` para uma data;
- taxa utilizada: `cotacaoVenda`;
- direção efetiva: BRL por 1 USD;
- fonte oficial e sem token.

### Serviço de domínio

Arquivo: `backend/app/services/fx_service.py`

- cache em memória;
- cache persistente em `fx_rates`;
- BCB/PTAX como fonte primária;
- AwesomeAPI como fallback;
- fallback numérico final fixo `5.70`;
- funções públicas para taxa atual, data específica e lote;
- UPSERT por `pair + rate_date`.

### Integrações redundantes ou legadas

1. `backend/app/integrations/fx_rate.py`
   - consulta direta à rota BRAPI `/quote/USDBRL=X`;
   - possui fallback numérico fixo;
   - é consumida pelo router `backend/app/routers/fx.py`;
   - duplica parcialmente o domínio já consolidado em `fx_service.py`.

2. `backend/app/integrations/brapi.py`
   - expõe `fetch_currency_rate()` via `/v2/currency`;
   - pode ser útil para cotação de mercado, mas não deve ser fonte histórica canônica do seed PTAX;
   - não deve ser acionada implicitamente pelo rebuild.

3. AwesomeAPI embutida em `fx_service.py`
   - fallback de disponibilidade, não fonte oficial;
   - uso precisa ser explícito na evidência do estágio;
   - dados de fallback não podem ser apresentados como PTAX.

## Consumidores confirmados

- `portfolio_service.py`: conversão histórica e atual de ativos USD;
- `portfolio_canonical_valuation_service.py`: conversão canônica de posições USD;
- `irpf_service.py`: possui fluxo cambial próprio baseado em `USDBRL=X` e fallback `1.0`, divergente do serviço canônico;
- `transactions`: armazena `fx_rate` por operação;
- router `fx.py`: usa integração BRAPI legada em vez de `fx_service.py`;
- snapshots, patrimônio e rentabilidade possuem referências monetárias e devem permanecer fora da escrita do seed.

## Inconsistências arquiteturais identificadas

1. `_db_set()` executa `commit()` e `rollback()` internamente. Isso impede reutilização segura pelo orquestrador transacional pré-produção.
2. `get_usd_brl_at_date()` e `get_usd_brl_batch()` fazem coleta, persistência, fallback e leitura no mesmo serviço.
3. Fallback fixo `5.70` pode ser persistido como se fosse taxa real na data atual.
4. AwesomeAPI pode ser persistida na mesma tabela sem coluna de origem, tornando impossível distinguir PTAX de fallback.
5. O model não registra `source`, `rate_type` ou horário de fixing.
6. `irpf_service.py` consulta `USDBRL=X` e retorna `1.0` quando falha, divergindo do contrato canônico.
7. `routers/fx.py` usa integração direta BRAPI legada e ignora cache e PTAX do serviço canônico.
8. Existem pelo menos três caminhos de obtenção de USD/BRL: BCB, BRAPI e AwesomeAPI, além de dois fallbacks fixos diferentes.

## Decisões para a Issue #217

- reutilizar `fx_rates`; nenhuma nova migration será criada neste estágio;
- par autorizado inicialmente: `USD-BRL`;
- convenção: quantidade de BRL por 1 USD;
- fonte canônica do seed: PTAX de venda do BCB;
- AwesomeAPI, BRAPI e fallback fixo não serão usados pelo seed auditável;
- o estágio escreverá somente `fx_rates`;
- o importador operacional deverá aceitar sessão externa e `commit=False`;
- nenhuma função que faça `commit()` interno poderá ser chamada diretamente pelo orquestrador;
- idempotência será medida pela variação real de `fx_rates`, duplicidades e cobertura final;
- limpeza dos caminhos legados será feita em blocos pequenos e separados do seed.

## Contrato operacional

Nome: `pre-prod-fx-seed.v1`.

Campos mínimos:

- identidade: `run_id`, branch e SHA completo;
- tabela autorizada: `fx_rates`;
- par: `USD-BRL`;
- direção: `BRL_PER_USD`;
- fonte: `BCB_PTAX_SELL`;
- janela solicitada e cobertura retornada;
- baseline e pós-contagem;
- criados, atualizados e inalterados;
- primeira e última data;
- duplicidades por `pair + rate_date`;
- taxas inválidas ou não positivas;
- pares não autorizados;
- erros e duração;
- `ok` somente após reconciliação completa.

## Próxima sequência

1. adaptar a persistência cambial para sessão externa e `commit=False`, preservando compatibilidade;
2. adicionar testes transacionais de commit, rollback e UPSERT;
3. criar contrato puro `pre-prod-fx-seed.v1`;
4. criar inspeção read-only de `fx_rates`;
5. criar orquestrador com advisory lock e transação única;
6. criar CLI, wrapper e comparador offline;
7. executar duas vezes e preservar evidências;
8. depois, eliminar ou redirecionar router e integrações legadas em commits próprios;
9. sincronizar README, ROADMAP, CHANGELOG e Issues #217, #216 e #158.
