# Inventário de deriva entre Alembic e MetaData — agosto de 2026

## Objetivo

Registrar a evidência obtida no banco PostgreSQL local descartável e impedir que o diff global seja convertido em uma migration automática monolítica.

## Evidência operacional

No HEAD `1e6276334dc27887bbeae3f0b5b69bbffe06d36c`:

- `alembic upgrade head` alcançou `20260731_corp_event_catalog` em banco vazio;
- `alembic current` confirmou `head`;
- a segunda execução de `upgrade head` foi idempotente;
- `alembic check` detectou deriva ampla entre o schema migrado e o `MetaData` ORM.

A cadeia de revisions está funcional. O bloqueio é de convergência global entre migrations e modelos.

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
| IRPF legado | `irpf_records` | tabela e índices seriam removidos | contrato migrado mensal preservado; runtime canônico não deve consumi-lo; remoção depende de evidência de dados | #56 / #241 |
| IRPF legado | `irpf_losses` | tabela e índice seriam removidos | contrato migrado mensal preservado; runtime canônico não deve consumi-lo; remoção depende de evidência de dados | #56 / #241 |
| Metas | `goal_allocations` | tabela e índice seriam removidos | contrato legado sem consumidor runtime comprovado; exige fixture antes de remoção | #241 |
| Ativos | `assets` | tipos, nulabilidade, índices, constraints, comentários e colunas | contrato divergente compartilhado | #129 / #130 / #241 |
| Proventos | `asset_dividends` | enum e índices divergentes | contrato divergente compartilhado | #226 / #241 |
| Eventos corporativos | `corporate_events` | JSONB/JSON, índices e unique constraint divergentes | contrato divergente compartilhado | #129 / #241 |
| Transações | `transactions` | tipos, nulabilidade, índices e colunas | alto risco financeiro | #56 / #241 |
| Metas | `goals` | colunas, tipos, FK, índices e colunas removidas | contrato divergente | #241 |
| Renda fixa | `fixed_income_investments` | comentários, nulabilidade e índice | contrato divergente | #241 |
| Posições | `portfolio_positions` | nulabilidade e índices | contrato divergente | #241 |
| Snapshots | `portfolio_snapshots` | comentários, nulabilidade e índices | contrato divergente | #241 |
| Taxas | `rate_history` | comentários, índice/constraint | provável diferença de representação | #241 |
| Auditoria | `audit_logs` | índices DESC vs ASC e índices ORM extras | provável diferença de representação e naming | #241 |
| Portfólios | `portfolios` | nulabilidade de timestamps | contrato divergente | #241 |
| Usuários | `users` | nulabilidade de timestamps | contrato divergente | #241 |
| Configuração | `system_configs` | nulabilidade de timestamps | contrato atual; consumidores consolidados | #241 |

## Decisão consolidada — `fx_rates`

- `fx_rates` não é tabela órfã nem schema legado descartável.
- O modelo `app.models.fx_rate.FxRate` está carregado pelo agregador `app.models` e, portanto, participa de `Base.metadata` no Alembic.
- O contrato preserva `UNIQUE (pair, rate_date)`, o índice ascendente `ix_fx_rates_pair_date` e o índice descendente `idx_fx_pair_date_desc`.
- Não criar nova migration nem reintroduzir outro modelo apenas para silenciar um diff histórico.
- Qualquer diferença futura deve ser reproduzida em banco vazio atualizado antes de alterar DDL.

## Fronteira protegida — `irpf_records` e `irpf_losses`

- As duas tabelas foram criadas pela migration inicial e representam uma granularidade mensal histórica por usuário e mercado.
- O IRPF canônico atual é carteira-scoped, read-only e calculado a partir dos leitores financeiros vigentes; não deve voltar a ler nem escrever essas tabelas.
- Um gate percorre `app/models`, `app/routers` e `app/services` para impedir consumidores runtime de `irpf_records` e `irpf_losses`.
- Não reintroduzir modelos ORM mensais apenas para fazer o `alembic check` convergir.
- Nenhuma remoção é autorizada antes de contagem de linhas, inventário de FKs, fixture sintética e decisão coordenada nas Issues #56 e #241.

### Evidência local necessária antes de uma decisão destrutiva

```sql
SELECT 'irpf_records' AS table_name, COUNT(*) AS row_count FROM irpf_records
UNION ALL
SELECT 'irpf_losses' AS table_name, COUNT(*) AS row_count FROM irpf_losses;
```

```sql
SELECT
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('irpf_records', 'irpf_losses')
ORDER BY tc.table_name, tc.constraint_name;
```

## Ordem segura de investigação

### Grupo A — contratos isolados restantes

1. coletar evidência de dados e FKs de `irpf_records` / `irpf_losses`;
2. coletar evidência de dados e FKs de `goal_allocations`;
3. decidir preservação, migração ou contração somente com fixture sintética.

### Grupo B — contratos financeiros e compartilhados

Tratar somente após inventário de consumidores:

- `assets`;
- `asset_dividends`;
- `corporate_events`;
- `transactions`;
- `portfolio_positions`;
- `portfolio_snapshots`.

### Grupo C — diferenças potencialmente cosméticas

- comentários;
- nomes equivalentes de constraints;
- ordenação explícita de índices;
- representação `JSON` vs `JSONB` somente após decisão arquitetural;
- índices ORM automáticos sobre PKs.

## Critérios para fechar #241

- todos os itens classificados;
- nenhum objeto válido aparece como remoção acidental;
- migrations e modelos convergem por domínio;
- `alembic check` limpo em banco criado do zero;
- reexecução idempotente;
- estrutura legada sintética validada;
- documentação e Issues sincronizadas.
