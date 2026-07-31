# Plano de migração do modelo de Proventos

Status: migração funcional concluída para direitos calculados sob demanda. A
contração física do schema legado permanece coordenada com o rebuild controlado
da Issue #158.

## Objetivo

Consolidar três responsabilidades sem perda de histórico:

1. `asset_dividends`: catálogo global de eventos de todos os ativos do banco;
2. direito por carteira: projeção calculada a partir de eventos e posição histórica;
3. reconhecimento financeiro: data e valor efetivamente recebidos, sem misturar eventos não monetários.

A coleta global não depende de posição em carteira. A elegibilidade é calculada
somente na leitura e não materializa linhas em `dividends`.

## Inventário obrigatório

Antes de cada etapa de migração, executar no backend:

```bash
python -m app.cli.audit_proventos_model
```

O comando é somente leitura e retorna JSON com:

| Métrica | Uso na contração |
| --- | --- |
| `asset_events` | confirma o volume preservado no catálogo canônico |
| `legacy_dividend_rows` | quantifica linhas de `dividends` que serão descartadas/reconstruídas |

As duas contagens são informativas para backup, reconstrução e remoção física.
Métricas de vínculo, duplicidade e divergência de materializações foram retiradas:
elas avaliavam uma representação que não será promovida ao modelo canônico.

### Evidência do ambiente de desenvolvimento — 19/07/2026

O antigo dry-run de vínculos foi executado pelo Docker Compose após rebuild da
`stable-15jun` e retornou:

```json
{
  "ambiguous": 0,
  "duplicate_right": 0,
  "invalid_identity": 0,
  "legacy_divergence": 0,
  "matched": 0,
  "no_candidate": 0,
  "scanned": 0
}
```

Conclusão: não havia direitos históricos sem `asset_dividend_id` nessa base e
nenhum backfill deveria ser aplicado. Depois da migração dos consumidores para
direitos calculados sob demanda, a rotina e sua CLI foram removidas. A auditoria
geral read-only permanece disponível antes da #158; nulabilidade e campos
legados continuam adiados para a contração controlada do schema.

## Mapeamento de campos

`DividendType` e `DividendStatus` vivem em `app.models.dividend_enums`, sem
dependência de SQLAlchemy. O ORM legado apenas importa esses objetos para mapear
a coluna existente e preservar compatibilidade durante a contração.

Os relacionamentos `Portfolio.dividends`, `AssetDividend.portfolio_dividends`,
`Dividend.portfolio` e `Dividend.asset_dividend` foram removidos após prova de
zero consumidores. As colunas e FKs permanecem até a migration de contração.

| Canônico em `dividends` | Legado temporário | Regra de transição |
| --- | --- | --- |
| `ex_date` | `date_ex` | comparar e preencher somente após resolver divergências |
| `payment_date` | `date_pagamento` | preservar nulos quando o evento ainda não possuir pagamento definido |
| `quantity` | `quantity_on_date` | recalcular pela data de corte canônica antes de escolher a origem |
| `value_per_unit` | `value_per_share` | validar contra o evento global vinculado |
| `total_value` / `net_value` | `total_received` | manter bruto e líquido explícitos; não inferir JCP pelo campo legado |

`asset_dividend_id` permanece anulável até que todos os registros históricos tenham vínculo validado. Não será preenchido apenas por coincidência de ticker e data quando houver mais de um candidato.

## Sequência segura

### 1. Expandir

- manter campos e tabelas existentes;
- adicionar apenas estruturas necessárias à rastreabilidade comprovada;
- não trocar a unicidade de `asset_dividends` sem casos reais por provedor.

### 2. Reconstruir

- reconstruir direitos a partir de `asset_dividends` e transações históricas;
- comparar resultados com o legado somente como evidência de migração;
- não vincular, reconciliar ou recriar linhas em `dividends`.

### 3. Validar

- executar o inventário antes e depois da reconstrução controlada;
- validar ações, FIIs, ETFs e BDRs separadamente;
- comprovar idempotência e isolamento por carteira;
- comparar os totais anteriores e posteriores por competência e tipo.

### 4. Restringir

- avaliar `NOT NULL` para `dividends.asset_dividend_id` somente com inventário zerado;
- avaliar unicidade por `(portfolio_id, asset_dividend_id)` após eliminar duplicidades;
- definir uma identidade de evento que suporte eventos legítimos do mesmo tipo e data antes de substituir `uq_asset_dividend_asset_exdate_type`.

### 5. Contrair

Somente durante a janela da #158, com backup e dry-run aprovados:

- remover os quatro campos legados já substituídos;
- remover `total_received` quando todos os consumidores usarem bruto/líquido explícitos;
- remover `dividends_sync_jobs` e seu modelo depois de confirmar inventário e histórico necessários;
- remover índices e código de compatibilidade sem consumidores.

## Critérios de bloqueio

A migração deve parar se houver:

- direito sem evento global e sem candidato inequívoco;
- duplicidade de materialização;
- divergência de quantidade ou valor sem fonte comprovada;
- perda de total financeiro por carteira/período;
- evento não monetário incluído nos KPIs financeiros.

## Registro de auditoria

O commit `fcc7bb34c22eb3a06673d68d2043c7818dfd94d1` removeu dois endpoints administrativos obsoletos que ainda importavam o sincronizador FII já excluído. Não havia consumidor no frontend. Esse achado corrige o diagnóstico anterior de ausência total de consumidores: existiam rotas administrativas residuais, embora não fossem parte do pipeline canônico.
