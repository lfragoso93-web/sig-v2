# Inventário de deriva entre Alembic e MetaData — agosto de 2026

## Objetivo

Registrar a evidência obtida no banco PostgreSQL local descartável e impedir que o diff global seja convertido em uma migration automática monolítica.

## Evidência operacional

No HEAD `1e6276334dc27887bbeae3f0b5b69bbffe06d36c`:

- `alembic upgrade head` alcançou `20260731_corp_event_catalog` em banco vazio;
- `alembic current` confirmou `head`;
- a segunda execução de `upgrade head` foi idempotente;
- `alembic check` detectou deriva ampla entre o schema migrado e o `MetaData` ORM.

Após as contrações validadas de `goal_allocations`, `irpf_losses` e `irpf_records`, o runtime permaneceu saudável e o novo `alembic check` deixou de propor operações para esses contratos. O diff remanescente passou a concentrar divergências de contratos compartilhados e diferenças cosméticas.

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
| Aliases | `asset_aliases.id` | índice `ix_asset_aliases_id` seria adicionado | `index=True` redundante removido da PK ORM; migration canônica mantém apenas PK | #241 |
| Proventos | `asset_dividends.id` | índice `ix_asset_dividends_id` seria adicionado | `index=True` redundante removido da PK ORM; demais índices e enum preservados | #226 / #241 |
| Auditoria | `audit_logs.id` | índice `ix_audit_logs_id` seria adicionado | `index=True` redundante removido da PK ORM; índices funcionais preservados | #241 |
| Snapshots | `portfolio_snapshots.id` | índice `ix_portfolio_snapshots_id` seria adicionado | `index=True` redundante removido da PK ORM; contrato funcional preservado | #241 |
| Preços | `asset_prices` | índice `idx_ap_asset_ts` seria removido | MetaData alinhado ao índice físico `(asset_id, timestamp DESC)` já criado pela migration `0020` | #241 |
| Auditoria | `audit_logs` | índices DESC vs ASC e índices ORM extras | MetaData alinhado aos índices físicos DESC; removidas somente declarações ORM dos índices simples ausentes | #241 |
| Snapshots | `idx_ps_portfolio_date_desc` | expressão DESC seria trocada por ASC | MetaData passou a usar `snapshot_date DESC` explicitamente | #241 |
| Ativos | `assets` | tipos, nulabilidade, índices, constraints, comentários e colunas | contrato divergente compartilhado | #129 / #130 / #241 |
| Proventos | `asset_dividends` | enum e índices divergentes | contrato divergente compartilhado além do PK já alinhado | #226 / #241 |
| Eventos corporativos | `corporate_events` | JSONB/JSON, índices e unique constraint divergentes | contrato divergente compartilhado | #129 / #241 |
| Transações | `transactions` | tipos, nulabilidade, índices e colunas | alto risco financeiro | #56 / #241 |
| Metas | `goals` | colunas, tipos, FK, índices e colunas removidas | contrato divergente | #241 |
| Renda fixa | `fixed_income_investments` | comentários, nulabilidade e índice | contrato divergente | #241 |
| Posições | `portfolio_positions` | nulabilidade e índices | contrato divergente | #241 |
| Snapshots | `portfolio_snapshots` | comentários, nulabilidade e índices | contrato divergente além dos índices já alinhados | #241 |
| Taxas | `rate_history` | comentários, índice/constraint | provável diferença de representação | #241 |
| Portfólios | `portfolios` | nulabilidade de timestamps | contrato divergente | #241 |
| Usuários | `users` | nulabilidade de timestamps | contrato divergente | #241 |
| Configuração | `system_configs` | nulabilidade de timestamps | contrato atual; consumidores consolidados | #241 |

## Decisão consolidada — `fx_rates`

- `fx_rates` não é tabela órfã nem schema legado descartável.
- O modelo `app.models.fx_rate.FxRate` está carregado pelo agregador `app.models` e, portanto, participa de `Base.metadata` no Alembic.
- O contrato preserva `UNIQUE (pair, rate_date)`, o índice ascendente `ix_fx_rates_pair_date` e o índice descendente `idx_fx_pair_date_desc`.
- Não criar nova migration nem reintroduzir outro modelo apenas para silenciar um diff histórico.
- Qualquer diferença futura deve ser reproduzida em banco vazio atualizado antes de alterar DDL.

## Contração isolada — schema mensal legado de IRPF

- `irpf_records` e `irpf_losses` foram criadas pela migration inicial, não possuem modelos ORM atuais nem consumidores runtime em models, routers ou services.
- A evidência PostgreSQL local confirmou zero linhas e FKs para `users.id` com `ON DELETE CASCADE`.
- A fixture sintética transacional validou ambas as tabelas e encerrou em `ROLLBACK`, mantendo zero persistência.
- As migrations `20260806_drop_irpf_losses` e `20260806_drop_irpf_records` foram validadas separadamente com upgrade, downgrade e reaplicação.
- Cada downgrade restaurou colunas, defaults, PK, FK e índices históricos.
- O enum compartilhado `irpfmarket` foi preservado.
- O `alembic check` final deixou de propor remoção de qualquer uma das duas tabelas.

## Contração isolada — `goal_allocations`

- A aplicação atual não expõe modelo, router, endpoint ou service para allocations por meta.
- A evidência local confirmou zero linhas e FK `goal_allocations_goal_id_fkey` para `goals.id`.
- A fixture PostgreSQL inseriu a cadeia sintética completa, validou a FK e encerrou em `ROLLBACK`, mantendo zero persistência.
- A migration `20260806_drop_goal_allocations` foi validada com upgrade, downgrade e reaplicação.
- O downgrade restaurou tabela, zero linhas e FK original; o reupgrade removeu novamente a tabela.
- O backend iniciou saudável no novo head e `goal_allocations` desapareceu do `alembic check`.

## Alinhamento cosmético — índices já existentes no schema

- `asset_aliases.id`, `asset_dividends.id`, `audit_logs.id` e `portfolio_snapshots.id` eram declarados no ORM como PK e também com `index=True`; os índices B-tree extras foram removidos somente do MetaData.
- `AssetPrice` passou a declarar `idx_ap_asset_ts (asset_id, timestamp DESC)`, já existente desde a migration `0020`.
- `AuditLog` passou a representar explicitamente `created_at DESC` nos índices compostos e deixou de pedir `ix_audit_logs_user_id`/`ix_audit_logs_portfolio_id`, inexistentes no schema migrado.
- `PortfolioSnapshot` passou a representar `idx_ps_portfolio_date_desc` com expressão `snapshot_date DESC` em vez de `postgresql_ops` que o autogenerate interpretava como ASC.
- Nenhuma migration, FK, enum, tabela ou dado foi alterado; gates dedicados protegem esses alinhamentos.

### Evidência local coletada em 06/08/2026

- `irpf_records`: 0 linhas antes da contração; FK `irpf_records_user_id_fkey` para `users.id`.
- `irpf_losses`: 0 linhas antes da contração; FK `irpf_losses_user_id_fkey` para `users.id`.
- `goal_allocations`: 0 linhas antes da contração; FK `goal_allocations_goal_id_fkey` para `goals.id`.
- Fixture sintética: 6 inserts aprovados, três cardinalidades iguais a 1, `ROLLBACK` confirmado e contagens finais iguais a zero.
- Três contratos legados: ciclos upgrade/downgrade/reupgrade aprovados.
- Runtime: backend saudável, PostgreSQL e Redis `ok`, `app.main` importado com sucesso.

## Ordem segura de investigação

### Grupo A — diferenças cosméticas de baixo risco

1. validar no novo `alembic check` que `idx_ap_asset_ts`, os índices DESC de auditoria e `idx_ps_portfolio_date_desc` deixaram de divergir;
2. revisar índices simples adicionais apenas quando a migration canônica e os consumidores comprovarem ownership;
3. alinhar representações comprovadamente equivalentes com gate dedicado;
4. não alterar tipos, nulabilidade ou colunas no mesmo bloco.

### Grupo B — contratos financeiros e compartilhados

Tratar somente após inventário de consumidores:

- `assets`;
- `asset_dividends`;
- `corporate_events`;
- `transactions`;
- `portfolio_positions`;
- `portfolio_snapshots`.

### Grupo C — diferenças potencialmente cosméticas restantes

- comentários;
- nomes equivalentes de constraints;
- representação `JSON` vs `JSONB` somente após decisão arquitetural;
- índices ORM automáticos não funcionais.

## Critérios para fechar #241

- todos os itens classificados;
- nenhum objeto válido aparece como remoção acidental;
- migrations e modelos convergem por domínio;
- `alembic check` limpo em banco criado do zero;
- reexecução idempotente;
- estrutura legada sintética validada;
- documentação e Issues sincronizadas.
