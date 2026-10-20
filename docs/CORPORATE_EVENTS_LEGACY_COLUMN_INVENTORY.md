# Inventário de colunas legadas de `corporate_events` (#272)

**Data:** 17/10/2026

**Tipo:** revisão estática read-only; sem consulta ao banco e sem DDL.

## Resultado

As colunas avaliadas não são aliases inertes em todos os fluxos. O catálogo
global novo já grava os campos canônicos e espelha `event_date`/`ratio`, mas o
fluxo de troca de ticker por carteira ainda usa diretamente vários campos
legados para idempotência e para materializar as transações históricas. Não
remover coluna enquanto esse consumidor existir.

| Coluna | Uso atual encontrado | Decisão estática |
|---|---|---|
| `event_date` | fallback do leitor para linhas `legacy`; data do evento em `ticker_change_processor`; escrita por `ticker_change_event_service` e como espelho do catálogo | ativa; manter |
| `ratio` | fallback do leitor quando `quantity_factor` falta; escrita na criação de troca de ticker e espelho do catálogo | ativa/compatibilidade; manter |
| `brapi_event_id` | fallback de identidade histórica; lookup idempotente da troca de ticker; escrita como chave da troca | ativa; manter |
| `raw_data` | fallback de payload do leitor; contém tickers antigo/novo para processar troca de ticker | ativa; manter |
| `applied_at` | escrito pelo processador para registrar aplicação/idempotência da troca de ticker | ativa; manter |
| `portfolio_id` | delimita eventos escopados por carteira; filtro global exclui estes eventos; preflight e processador usam o vínculo | ativa e semanticamente necessária; manter |

Referências principais:

- `backend/app/services/ticker_change_event_service.py` cria o evento de troca
  com `portfolio_id`, `event_date`, `ratio`, `brapi_event_id` e `raw_data`;
- `backend/app/services/ticker_change_processor.py` lê `portfolio_id`,
  `raw_data` e `event_date`, e atualiza `applied_at`;
- `backend/app/services/corporate_action_position_reader.py` mantém fallback
  controlado para `event_date`, `ratio`, `brapi_event_id` e `raw_data`, e exclui
  explicitamente eventos com `portfolio_id` do catálogo global;
- `backend/app/services/corporate_event_ledger_preflight.py` resolve a carteira
  do evento para o preflight;
- `backend/tests/test_corporate_event_legacy_field_boundary.py` impede novos
  consumidores fora da camada de compatibilidade;
- `backend/alembic/versions/20260731_corporate_event_catalog.py` adiciona o
  catálogo canônico e copia `event_date` para `effective_date` e `ratio` para
  `quantity_factor`, sem remover os campos de origem.

## Implicações para #272

O código correspondente também está presente na branch remota `stable-15jun`.
A Issue deve ser dividida em três marcos para que a limpeza não concorra com um
consumidor ativo:

1. **Separar o evento por carteira:** introduzir um armazenamento próprio para
   `TICKER_CHANGE`, migrar os registros escopados e apontar criação, lookup
   idempotente, aplicação e status para esse contrato. Preservar ownership,
   `effective_date`, old/new ticker, status, instante de aplicação e a geração
   transacional com marcador idempotente. Manter leitura compatível durante a
   transição e reconciliar origem/destino antes de retirar o caminho antigo.
2. **Convergir o catálogo global:** remover consumidores/fallbacks para
   `event_date`, `ratio`, `brapi_event_id` e `raw_data`; confirmar em inventário
   que os campos canônicos (`effective_date`, `quantity_factor`,
   `source_event_id`, `raw_metadata`) preservam integralmente as linhas globais.
3. **Preparar contração física:** só depois de não haver leitores ou escritores
   desses campos, consultar em modo read-only schema, contagens, nullability e
   conteúdo na base alvo; reconciliar backup/restore e então propor migration
   governada, com testes isolados e janela explícita.

`applied_at` e `portfolio_id` não podem ser classificados como removíveis sem
concluir o marco 1. Nenhuma etapa deste plano foi executada neste inventário.

Nenhum dado, migration histórica, schema runtime ou projeção financeira foi
alterado. Este inventário não autoriza remoção de coluna.
