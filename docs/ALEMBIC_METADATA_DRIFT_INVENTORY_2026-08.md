# Inventário de deriva entre Alembic e MetaData — agosto de 2026

## Objetivo

Registrar a evidência obtida no banco PostgreSQL local descartável e impedir que o diff global seja convertido em uma migration automática monolítica.

## Evidência operacional

No HEAD `1e6276334dc27887bbeae3f0b5b69bbffe06d36c`:

- `alembic upgrade head` alcançou `20260731_corp_event_catalog` em banco vazio;
- `alembic current` confirmou `head`;
- a segunda execução de `upgrade head` foi idempotente;
- `alembic check` detectou deriva ampla entre o schema migrado e o `MetaData` ORM.

Após as contrações validadas de `goal_allocations`, `irpf_losses` e `irpf_records`, o runtime permaneceu saudável e o novo `alembic check` deixou de propor operações para esses contratos. Os lotes seguintes removeram ruído de índices redundantes/representações divergentes sem alterar DDL.

## Regras de tratamento

1. Não gerar migration automática com o diff completo.
2. Não remover tabelas apenas porque estão ausentes do `MetaData` carregado.
3. Confirmar consumidores e ownership antes de qualquer contração.
4. Separar migration ausente, modelo legado, schema legado preservado e diferença cosmética.
5. Tratar um domínio ou contrato por commit.
6. Toda mudança destrutiva exige fixture sintética e validação de dados.

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
| Posições | `portfolio_positions` | `idx_pp_portfolio` seria removido e `ix_portfolio_positions_asset_id` adicionado | MetaData alinhado ao índice físico histórico; índice ORM inexistente de `asset_id` removido | #241 |
| Alocação | `portfolio_class_targets` | `idx_pct_portfolio` seria removido | MetaData passa a descrever o índice físico criado pela migration de performance | #241 |
| Taxas | `rate_history` | comentários e troca índice único ↔ unique constraint | MetaData alinhado à migration `014`: índice único físico e comentários canônicos | #241 |
| Renda fixa | `fixed_income_investments` | comentário, timestamps e índice simples ORM | comentário de `daily_liquidity` alinhado; índice ORM inexistente de `portfolio_id` removido; timestamps ainda pendentes | #241 |
| Snapshots | `portfolio_snapshots` | comentários, nulabilidade e índices simples | MetaData agora preserva os três índices da migration `005` e o índice DESC; comentários/timestamps ainda pendentes | #241 |
| Ativos | `assets` | tipos, nulabilidade, índices, constraints, comentários e colunas | contrato divergente compartilhado | #129 / #130 / #241 |
| Proventos | `asset_dividends` | enum e índices divergentes | contrato divergente compartilhado além do PK já alinhado | #226 / #241 |
| Eventos corporativos | `corporate_events` | JSONB/JSON, índices e unique constraint divergentes | contrato divergente compartilhado | #129 / #241 |
| Transações | `transactions` | tipos, nulabilidade, índices e colunas | alto risco financeiro | #56 / #241 |
| Metas | `goals` | colunas, tipos, FK, índices e colunas removidas | contrato divergente | #241 |
| Portfólios | `portfolios` | nulabilidade de timestamps | contrato divergente | #241 |
| Usuários | `users` | nulabilidade de timestamps | contrato divergente | #241 |
| Configuração | `system_configs` | nulabilidade de timestamps | contrato atual; consumidores consolidados | #241 |

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

## Alinhamentos cosméticos e de índices já concluídos

- Removidos índices ORM redundantes de PK em `asset_aliases`, `asset_dividends`, `audit_logs` e `portfolio_snapshots`.
- `asset_prices` passou a representar `idx_ap_asset_ts (asset_id, timestamp DESC)`.
- `audit_logs` passou a representar os índices compostos com `created_at DESC`, sem pedir índices simples extras de `user_id`/`portfolio_id`.
- `portfolio_positions` preserva `idx_pp_portfolio` e deixou de pedir índice simples inexistente em `asset_id`.
- `portfolio_class_targets` preserva `idx_pct_portfolio` criado pela migration `0020`.
- `rate_history` passou a representar `uq_rate_history_indicator_date` como índice único, exatamente como a migration `014`.
- `fixed_income_investments` deixou de pedir índice simples inexistente de `portfolio_id` e passou a refletir o comentário da migration `015`.
- `portfolio_snapshots` passou a representar os três índices de consulta da migration `005` e `idx_ps_portfolio_date_desc` com expressão DESC real.
- Todos esses ajustes alteram somente MetaData/testes/documentação; nenhum DDL ou dado foi modificado.

## Ordem segura de investigação

### Grupo A — diferenças de baixo risco restantes

1. validar que `rate_history`, `fixed_income_investments.portfolio_id` e os três índices simples de snapshots desapareceram do diff;
2. tratar nulabilidade de timestamps apenas após decisão explícita sobre `TimestampMixin` versus schema histórico;
3. não combinar tipo, nulabilidade e colunas no mesmo bloco.

### Grupo B — contratos financeiros e compartilhados

Tratar somente após inventário de consumidores e migrations:

- `assets`;
- `asset_dividends`;
- `corporate_events`;
- `transactions`;
- `goals`;
- `portfolio_snapshots`.

## Critérios para fechar #241

- todos os itens classificados;
- nenhum objeto válido aparece como remoção acidental;
- migrations e modelos convergem por domínio;
- `alembic check` limpo em banco criado do zero;
- reexecução idempotente;
- estrutura legada sintética validada;
- documentação e Issues sincronizadas.
