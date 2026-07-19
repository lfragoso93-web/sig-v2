# Plano de migração do modelo de Proventos

Status: preparação em andamento na Issue #165. A contração física do schema depende do rebuild controlado da Issue #158.

## Objetivo

Consolidar três responsabilidades sem perda de histórico:

1. `asset_dividends`: catálogo global de eventos de todos os ativos do banco;
2. `dividends`: direito materializado e rastreável de uma carteira;
3. reconhecimento financeiro: data e valor efetivamente recebidos, sem misturar eventos não monetários.

A coleta global não depende de posição em carteira. A elegibilidade é aplicada apenas na materialização de `dividends`.

## Inventário obrigatório

Antes de cada etapa de migração, executar no backend:

```bash
python -m app.cli.audit_proventos_model
python -m app.cli.dry_run_proventos_legacy_links --summary-only
```

O comando é somente leitura e retorna JSON com:

| Métrica | Risco identificado |
| --- | --- |
| `unlinked_portfolio_rights` | direitos sem rastreabilidade para um evento global |
| `duplicate_materialization_groups` | mais de um direito para a mesma carteira e evento |
| `*_mismatches` | divergência entre campos canônicos e legados |
| `legacy_sync_job_rows` | estado residual do antigo sincronizador exclusivo de FIIs |

As contagens de eventos e direitos são informativas. As demais precisam ser explicadas ou zeradas antes da contração.

O segundo comando simula o vínculo dos direitos sem evento. Remover
`--summary-only` inclui cada decisão e os IDs dos eventos candidatos. Ele não
possui opção de aplicação e não executa `UPDATE`, `flush` ou `commit`.

Resultados possíveis do dry-run:

| Status | Significado |
| --- | --- |
| `matched` | existe um único candidato estrito e não há colisão na carteira |
| `no_candidate` | nenhum evento global possui a mesma identidade |
| `ambiguous` | mais de um evento global atende aos critérios |
| `legacy_divergence` | campos canônicos e legados do direito divergem |
| `invalid_identity` | faltam dados obrigatórios ou o tipo não é normalizável com segurança |
| `duplicate_right` | a carteira já possui ou passaria a possuir dois direitos para o evento |

## Mapeamento de campos

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

### 2. Backfill

- ligar direitos históricos a eventos globais com critérios determinísticos;
- registrar ambiguidades para decisão manual/rebuild;
- sincronizar pares canônico/legado apenas quando a origem estiver comprovada.

O dry-run atual exige ticker, data ex, tipo e valor por unidade iguais. Quando
direito e evento possuem data de pagamento, ela também precisa coincidir. O
vínculo só poderá ser aplicado futuramente aos registros classificados como
`matched`, após revisão do relatório real.

### 3. Validar

- executar o inventário antes e depois do backfill;
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
