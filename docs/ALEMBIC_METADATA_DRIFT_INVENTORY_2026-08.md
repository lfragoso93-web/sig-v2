# Inventário de deriva entre Alembic e MetaData — agosto de 2026

## Objetivo

Registrar a evidência obtida no banco PostgreSQL local descartável e impedir que o diff global seja convertido em uma migration automática monolítica.

## Evidência operacional

No HEAD `1e6276334dc27887bbeae3f0b5b69bbffe06d36c`:

- `alembic upgrade head` alcançou `20260731_corp_event_catalog` em banco vazio;
- `alembic current` confirmou `head`;
- a segunda execução de `upgrade head` foi idempotente;
- `alembic check` detectou deriva ampla entre o schema migrado e o `MetaData` ORM.

Após as contrações validadas de `goal_allocations`, `irpf_losses` e `irpf_records`, o runtime permaneceu saudável e o novo `alembic check` deixou de propor operações para esses contratos. Os lotes seguintes removeram progressivamente ruído de índices, comentários, tipos de representação e colunas físicas já migradas, mantendo mudanças destrutivas separadas.

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
| Posições | `portfolio_positions` | `idx_pp_portfolio` seria removido e `ix_portfolio_positions_asset_id` adicionado | índices alinhados; somente nulabilidade dos timestamps permanece | #241 |
| Alocação | `portfolio_class_targets` | `idx_pct_portfolio` seria removido | MetaData passa a descrever o índice físico criado pela migration de performance | #241 |
| Taxas | `rate_history` | comentários e troca índice único ↔ unique constraint; banco preservado também possui índice duplicado `ix_rate_history_indicator_date_unique` | MetaData alinhado à migration `014`; migration defensiva remove apenas o índice físico duplicado quando o canônico `uq_rate_history_indicator_date` existe | #241 |
| Renda fixa | `fixed_income_investments` | comentário, timestamps e índice simples ORM | comentário e índice resolvidos; somente nulabilidade dos timestamps permanece | #241 |
| Snapshots | `portfolio_snapshots` | comentários, nulabilidade e índices | índices e comentários alinhados às migrations `005`/`20260713`; somente nulabilidade dos timestamps permanece | #241 |
| Ativos | `assets` | nulabilidade, índices, constraints, comentários, tipo de timestamp e colunas físicas omitidas | `updated_at`/`isin_code`, índices, unique `(ticker, asset_type)`, `currency` e comentários de cache alinhados; `created_at` timezone ainda pendente | #129 / #130 / #241 |
| Proventos | `asset_dividends` | enum e índices divergentes | índices físicos `idx_ad_asset_exdate_desc` e `ix_asset_dividends_approved_on` alinhados; enum `dividend_type` permanece pendente | #226 / #241 |
| Eventos corporativos | `corporate_events` | JSONB/JSON, índices e unique constraint divergentes | JSONB, quatro índices e `uq_corporate_events_source_identity` alinhados à migration canônica | #129 / #241 |
| Transações | `transactions` | tipos, nulabilidade, índices e colunas | todos os índices migrados refletidos; tipos financeiros, `fees`, `notes` e timestamps continuam pendentes | #56 / #241 |
| Metas | `goals` | colunas, tipos, FK, índices e colunas removidas | contrato divergente de alto risco ainda não tratado | #241 |
| Portfólios | `portfolios` | nulabilidade de timestamps | pendente decisão de endurecimento físico para `NOT NULL` | #241 |
| Usuários | `users` | nulabilidade de timestamps | pendente decisão de endurecimento físico para `NOT NULL` | #241 |
| Configuração | `system_configs` | nulabilidade de timestamps | contrato atual; pendente decisão de endurecimento físico para `NOT NULL` | #241 |

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
- `asset_dividends` representa os índices das migrations `021` e `027` sem alterar o enum ainda pendente.
- `transactions` representa `ix_transactions_portfolio_id`, os índices de `0020` e `idx_txn_portfolio_date_asc` de `021`, sem tocar nos tipos financeiros.
- `corporate_events` representa JSONB, os quatro índices e a unique constraint definidos pela `20260731_corp_event_catalog`.
- `assets` voltou a refletir colunas e índices já existentes (`updated_at`, `isin_code`, cache de preço e provider), além do nome físico `uq_asset_ticker_type` e `currency NOT NULL`.

## Limpeza física isolada — `rate_history`

A migration `20260807_drop_dup_rate_idx` trata apenas bancos preservados que possuem o índice órfão `ix_rate_history_indicator_date_unique` além do índice canônico `uq_rate_history_indicator_date`.

- upgrade verifica a existência do índice canônico antes de qualquer drop;
- se o duplicado não existir, o upgrade é idempotente;
- se o duplicado existir sem o canônico, a migration aborta;
- downgrade recria somente o índice redundante removido;
- nenhuma linha de `rate_history` é modificada.

## Próxima decisão estrutural — timestamps

A migration inicial criou `created_at`/`updated_at` com `DEFAULT now()` porém sem `NOT NULL` em `users`, `portfolios`, `fixed_income_investments`, `portfolio_positions` e `system_configs`; `portfolio_snapshots` seguiu o mesmo padrão na migration `005`. O `TimestampMixin` atual exige `nullable=False`.

A decisão recomendada é **não afrouxar o mixin**. Antes de uma migration de endurecimento:

1. contar linhas com `created_at IS NULL OR updated_at IS NULL` em cada tabela;
2. bloquear a migration se qualquer linha inválida existir;
3. aplicar `NOT NULL` em blocos pequenos e reversíveis;
4. validar downgrade e reaplicação antes de avançar para contratos financeiros.

## Ordem segura de investigação

### Grupo A — próximo bloco

1. certificar o lote MetaData-only atual;
2. aplicar e validar `20260807_drop_dup_rate_idx` com upgrade/downgrade/reaplicação;
3. coletar evidência read-only de nulabilidade dos timestamps;
4. somente então publicar migrations de endurecimento `NOT NULL`.

### Grupo B — contratos financeiros e compartilhados

Tratar somente após o bloco de timestamps:

- `asset_dividends.dividend_type`;
- `assets.created_at` timezone;
- `transactions` tipos/nullable/colunas históricas;
- `goals`;
- diferenças remanescentes de contratos financeiros.

## Critérios para fechar #241

- todos os itens classificados;
- nenhum objeto válido aparece como remoção acidental;
- migrations e modelos convergem por domínio;
- `alembic check` limpo em banco criado do zero;
- reexecução idempotente;
- estrutura legada sintética validada;
- documentação e Issues sincronizadas.
