# Alinhamento Alembic/MetaData — transactions — agosto de 2026

## Contexto

A Issue #241 reduziu o `alembic check` até restarem principalmente os contratos de `transactions` e `goals`.

A cadeia Alembic de `transactions` preserva um contrato financeiro de alta precisão:

- `asset_type VARCHAR(30)`;
- `quantity NUMERIC(18,8)`;
- `price NUMERIC(18,8)`;
- `fees NUMERIC(18,2) NOT NULL DEFAULT 0`;
- `notes TEXT`;
- `created_at` e `updated_at` como `TIMESTAMPTZ DEFAULT now()`.

A migration `006_tx_ticker_based` substituiu a identidade antiga baseada em `asset_id` pela identidade ticker-based, mas preservou os campos financeiros e de auditoria acima.

## Decisão arquitetural

O schema migrado permanece canônico para precisão financeira e auditabilidade. O ORM não deve converter valores monetários para `Float`, ampliar `asset_type` sem migration, tornar `fees` nullable nem omitir timestamps físicos.

O alinhamento é MetaData-only: nenhuma migration ou dado é alterado.

## Blocos

- `190fd45514e1e280e1249056f5d7c197853d43b1` — modelo `Transaction` alinhado aos tipos e colunas físicas;
- `802ab9a6e3959d13b96bd30ea55612489a73604c` — gate de precisão financeira e timestamps.

## Gates

`test_transaction_schema_contract_alignment.py` impede regressões que:

- convertam `quantity`, `price` ou `fees` para `Float`;
- alterem `asset_type` de `VARCHAR(30)` sem migration;
- substituam `notes TEXT` por limite artificial;
- removam `created_at`/`updated_at` do MetaData.

## Próximo domínio

`goals` não pode ser tratado como simples alinhamento MetaData-only. O serviço atual depende de colunas ausentes do schema migrado e usa uma taxonomia de tipos diferente do enum PostgreSQL legado. Antes de qualquer DDL, é obrigatório inventariar dados e valores de `goal_type` em PostgreSQL.