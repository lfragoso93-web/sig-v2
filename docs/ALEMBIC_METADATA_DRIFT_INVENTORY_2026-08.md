# Inventário de deriva entre Alembic e MetaData — agosto de 2026

## Objetivo

Registrar a evidência obtida no banco PostgreSQL local descartável e impedir que o diff global seja convertido em uma migration automática monolítica.

## Evidência operacional

No HEAD `1e6276334dc27887bbeae3f0b5b69bbffe06d36c`:

- `alembic upgrade head` alcançou `20260731_corp_event_catalog` em banco vazio;
- `alembic current` confirmou `head`;
- a segunda execução de `upgrade head` foi idempotente;
- `alembic check` detectou deriva ampla entre o schema migrado e o `MetaData` ORM.

Após as contrações validadas de `goal_allocations`, `irpf_losses` e `irpf_records`, o runtime permaneceu saudável e o novo `alembic check` deixou de propor operações para esses contratos. Os lotes seguintes removeram progressivamente ruído de índices, comentários, tipos de representação, timestamps e colunas físicas já migradas, mantendo mudanças destrutivas separadas.

## Regras de tratamento

1. Não gerar migration automática com o diff completo.
2. Não remover tabelas apenas porque estão ausentes do `MetaData` carregado.
3. Confirmar consumidores e ownership antes de qualquer contração.
4. Separar migration ausente, modelo legado, schema legado preservado e diferença cosmética.
5. Tratar um domínio ou contrato por commit.
6. Toda mudança destrutiva exige fixture sintética e validação de dados.
7. Não adaptar o ORM a artefatos físicos órfãos de um banco preservado quando a cadeia Alembic canônica comprova outro contrato.

## Matriz atual

| Domínio | Objeto | Sintoma original no `alembic check` | Classificação atual | Issue |
|---|---|---|---|---|
| Configuração | `app_config` | tabela e índices seriam adicionados | modelo duplicado removido; consumidores migrados para `system_configs` | #241 |
| IRPF | `irpf_reports` | tabela e índice seriam adicionados | modelo órfão removido; fachada histórica read-only em memória | #56 / #241 |
| Câmbio | `fx_rates` | tabela e índices seriam removidos | contrato persistido atual, registrado no MetaData por `FxRate`; índices e unicidade protegidos por gates | #241 |
| IRPF legado | `irpf_records` | tabela e índices seriam removidos | contração aplicada e validada; não aparece mais no diff | #242 / #241 |
| IRPF legado | `irpf_losses` | tabela e índice seriam removidos | contração aplicada e validada; não aparece mais no diff | #242 / #241 |
| Metas | `goal_allocations` | tabela e índice seriam removidos | contração aplicada e validada; não aparece mais no diff | #241 |
| Aliases | `asset_aliases.id` | índice `ix_asset_aliases_id` seria adicionado | índice redundante de PK removido do ORM | #241 |
| Proventos | `asset_dividends.id` | índice `ix_asset_dividends_id` seria adicionado | índice redundante de PK removido do ORM | #226 / #241 |
| Auditoria | `audit_logs.id` | índice `ix_audit_logs_id` seria adicionado | índice redundante de PK removido do ORM | #241 |
| Snapshots | `portfolio_snapshots.id` | índice `ix_portfolio_snapshots_id` seria adicionado | índice redundante de PK removido do ORM | #241 |
| Preços | `asset_prices` | `idx_ap_asset_ts` seria removido | MetaData alinhado ao índice físico `(asset_id, timestamp DESC)` | #241 |
| Auditoria | `audit_logs` | índices DESC vs ASC e índices simples extras | MetaData alinhado aos índices físicos DESC; índices simples inexistentes removidos do ORM | #241 |
| Posições | `portfolio_positions` | índice e nulabilidade divergentes | índices alinhados e timestamps endurecidos para `NOT NULL` com validação PostgreSQL | #241 |
| Alocação | `portfolio_class_targets` | `idx_pct_portfolio` seria removido | MetaData passa a descrever o índice físico criado pela migration de performance | #241 |
| Taxas | `rate_history` | comentários e troca índice único ↔ unique constraint; banco preservado também possuía índice duplicado | MetaData alinhado à migration `014`; índice físico redundante removido por migration defensiva e certificada | #241 |
| Renda fixa | `fixed_income_investments` | comentário, timestamps e índice simples ORM | comentário/índice alinhados e timestamps endurecidos para `NOT NULL` | #241 |
| Snapshots | `portfolio_snapshots` | comentários, nulabilidade e índices | índices/comentários alinhados e timestamps endurecidos para `NOT NULL` | #241 |
| Ativos | `assets` | nulabilidade, índices, constraints, comentários, tipo de timestamp e colunas físicas omitidas | colunas, índices, unique, currency, comentários e `created_at TIMESTAMPTZ` alinhados ao schema físico | #129 / #130 / #241 |
| Proventos | `asset_dividends` | enum e índices divergentes | índices alinhados; `dividend_type` preserva `DividendType` em Python com armazenamento `VARCHAR(20)` não nativo | #226 / #241 |
| Eventos corporativos | `corporate_events` | JSONB/JSON, índices e unique constraint divergentes | JSONB, quatro índices e `uq_corporate_events_source_identity` alinhados à migration canônica | #129 / #241 |
| Transações | `transactions` | tipos, nulabilidade, índices e colunas | todos os índices migrados refletidos; tipos financeiros, `fees`, `notes` e timestamps continuam pendentes | #56 / #241 |
| Metas | `goals` | colunas, tipos, FK, índices e colunas removidas | contrato divergente de alto risco ainda não tratado | #241 |
| Portfólios | `portfolios` | nulabilidade de timestamps | endurecido para `NOT NULL` após evidência de zero `NULL` | #241 |
| Usuários | `users` | nulabilidade de timestamps | endurecido para `NOT NULL` após evidência de zero `NULL` | #241 |
| Configuração | `system_configs` | nulabilidade de timestamps | endurecido para `NOT NULL` após evidência de zero `NULL` | #241 |

## Decisão consolidada — `fx_rates`

- `fx_rates` não é tabela órfã nem schema legado descartável.
- O modelo `app.models.fx_rate.FxRate` está carregado pelo agregador `app.models` e participa de `Base.metadata` no Alembic.
- O contrato preserva `UNIQUE (pair, rate_date)`, `ix_fx_rates_pair_date` e `idx_fx_pair_date_desc`.
- Não criar nova migration nem reintroduzir outro modelo apenas para silenciar diff histórico.

## Contrações isoladas já certificadas

- `goal_allocations`, `irpf_losses` e `irpf_records` foram contraídos por migrations separadas, defensivas e reversíveis.
- A fixture sintética PostgreSQL validou seus vínculos e encerrou em `ROLLBACK`.
- Upgrade, downgrade e reaplicação foram validados; runtime permaneceu saudável.
- Os três contratos deixaram de aparecer no `alembic check`.

## Alinhamentos MetaData-only já concluídos

- Removidos índices ORM redundantes de PK em `asset_aliases`, `asset_dividends`, `audit_logs` e `portfolio_snapshots`.
- `asset_prices` passou a representar `idx_ap_asset_ts (asset_id, timestamp DESC)`.
- `audit_logs` passou a representar os índices compostos com `created_at DESC`, sem pedir índices simples extras de `user_id`/`portfolio_id`.
- `portfolio_positions` preserva `idx_pp_portfolio` e deixou de pedir índice simples inexistente em `asset_id`.
- `portfolio_class_targets` preserva `idx_pct_portfolio` criado pela migration `0020`.
- `rate_history` representa `uq_rate_history_indicator_date` como índice único, exatamente como a migration `014`, e preserva os comentários físicos.
- `fixed_income_investments` deixou de pedir índice simples inexistente de `portfolio_id` e reflete o comentário da migration `015`.
- `portfolio_snapshots` representa os índices das migrations `005`/`021`; comentários históricos coincidem com `005` e campos TWR adicionados por `20260713` não inventam comentários físicos ausentes.
- `asset_dividends` representa os índices das migrations `021` e `027` e preserva `VARCHAR(20)` como armazenamento de `dividend_type` sem perder `DividendType` no runtime.
- `transactions` representa `ix_transactions_portfolio_id`, os índices de `0020` e `idx_txn_portfolio_date_asc` de `021`, sem tocar nos tipos financeiros.
- `corporate_events` representa JSONB, os quatro índices e a unique constraint definidos pela `20260731_corp_event_catalog`.
- `assets` reflete colunas e índices já existentes, o nome físico `uq_asset_ticker_type`, `currency NOT NULL` e `created_at` com timezone.

## Limpeza física isolada — `rate_history`

A migration `20260807_drop_dup_rate_idx` tratou bancos preservados que possuíam o índice órfão `ix_rate_history_indicator_date_unique` além do índice canônico `uq_rate_history_indicator_date`.

- upgrade verificou a existência do índice canônico antes do drop;
- downgrade recriou somente o índice redundante removido;
- upgrade/downgrade/reaplicação foram certificados localmente;
- nenhuma linha de `rate_history` foi modificada.

## Endurecimento certificado — timestamps compartilhados

A evidência PostgreSQL confirmou zero linhas nulas em `users`, `portfolios`, `system_configs`, `fixed_income_investments`, `portfolio_positions` e `portfolio_snapshots`.

As migrations `20260807_users_portfolios_ts_nn`, `20260807_config_fixed_ts_nn` e `20260807_pos_snap_ts_nn`:

- abortam se qualquer timestamp nulo existir;
- não executam backfill silencioso;
- tornam `created_at`/`updated_at` `NOT NULL`;
- possuem downgrade reversível para `nullable=True`;
- foram certificadas por upgrade, downgrade isolado e reaplicação;
- eliminaram essas divergências do `alembic check`.

## Ordem segura de investigação

### Grupo A — contratos finais de alto risco

1. `transactions`: revisar impacto de `NUMERIC`/`TEXT`/timestamps sobre serviços e DTOs antes de alinhar ORM;
2. `goals`: reconciliar schema histórico e modelo atual, incluindo colunas novas, enum, FK e `is_active`/timestamps;
3. executar `alembic check` limpo em banco criado do zero;
4. suíte completa e certificação final.

## Critérios para fechar #241

- todos os itens classificados;
- nenhum objeto válido aparece como remoção acidental;
- migrations e modelos convergem por domínio;
- `alembic check` limpo em banco criado do zero;
- reexecução idempotente;
- estrutura legada sintética validada;
- documentação e Issues sincronizadas.
