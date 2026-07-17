# Rebuild Canônico de Mercado — Julho de 2026

## Objetivo

Consolidar uma arquitetura DB-first em que snapshots, KPIs e gráficos leem somente dados persistidos, com fontes oficiais para o histórico doméstico e motores dedicados por classe de ativo.

## Arquitetura final

```text
B3 COTAHIST ───────────────┐
Tesouro Transparente ──────┤
Motor de Renda Fixa ───────┤
Provedores complementares ─┤
                           ↓
                     Dados persistidos
                           ↓
                  Valuation canônico
                           ↓
                 Snapshots + TWR diário
                           ↓
         Resumo / Patrimônio / Rentabilidade
```

## Renda variável brasileira

Ações, FIIs, ETFs nacionais e BDRs utilizam o B3 COTAHIST como fonte histórica primária.

Características:

- leitura anual em lote;
- download único por arquivo anual;
- filtro pelos ativos canônicos já cadastrados;
- mercado à vista priorizado sobre fracionário;
- upsert por `asset_id + timestamp`;
- origem `b3_cotahist`;
- preservação de ativos deslistados;
- atualização de `last_price`.

Validação inicial:

- 2.258 ativos brasileiros processados;
- 984.949 preços recebidos e inseridos;
- 2.255 ativos classificados como completos;
- uma pré-listagem;
- um deslistado;
- um ativo sem histórico;
- nenhuma lacuna interna real.

## Ciclo de negociação

Estados:

- `COMPLETE`: série cobre o período necessário;
- `PRE_LISTING`: posição registrada antes da primeira cotação oficial;
- `DELISTED`: série encerrou porque o ativo deixou de negociar;
- `REAL_GAP`: falta preço entre a primeira e a última cotação;
- `NO_HISTORY`: nenhum histórico disponível.

Regra de valuation para pré-listagem:

- usar o custo médio da posição;
- não emitir warning;
- não marcar `has_partial_prices`;
- não marcar `return_is_estimated`.

## Tesouro Direto

O Treasury Catalog v2 utiliza o Tesouro Transparente como fonte principal.

Fluxo:

```text
Tesouro Transparente
    ↓
catálogo oficial
    ↓
normalização comercial
    ↓
asset_prices
    ↓
valuation do snapshot
```

Regras especiais:

- RendA+ usa o ano comercial de início dos pagamentos, não o vencimento final;
- Educa+ usa o ano comercial de início dos pagamentos;
- aliases antigos são mantidos para auditoria, mas não participam da coleta;
- Brapi é fallback secundário;
- preços oficiais são reconstruíveis de forma idempotente.

Validação:

- 150 títulos oficiais;
- 46 transações reconhecidas;
- nenhuma transação para revisão;
- 88.181 preços reconstruídos;
- três títulos abertos resolvidos no snapshot;
- nenhum título aberto não resolvido.

## Renda Fixa

Renda Fixa não usa `asset_prices` genérico.

O motor:

- reconstrói aplicações;
- aplica resgates em ordem;
- calcula principal em aberto;
- valoriza por indexadores e regras contratuais;
- retorna principal, valor atual e rendimento.

O valuation canônico substitui o proxy por custo pelo saldo corrigido.

## Snapshots e TWR

Cada dia útil persiste:

- patrimônio;
- custo base;
- investido líquido;
- ganho realizado;
- ganho não realizado;
- resultado total;
- fluxo externo líquido;
- proventos do dia;
- proventos acumulados;
- TWR diário;
- TWR acumulado;
- cobertura parcial;
- retorno estimado.

O TWR é calculado diariamente e composto para períodos mensais, 12 meses e desde o início.

## Resultado financeiro

Resultado não é sinônimo de rentabilidade.

```text
Resultado = ganho realizado + ganho não realizado + proventos recebidos
```

A rentabilidade percentual usa TWR para neutralizar aportes e resgates externos.

## Comandos

```bash
python -m app.cli.full_market_rebuild
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.audit_treasury_catalog_v2
```

## Idempotência

Todas as cargas usam chaves únicas e upserts. Uma segunda execução deve manter os dados sem duplicar preços, ativos ou snapshots.

## Próxima auditoria

A próxima etapa funcional é confrontar os cards da página Resumo com o último snapshot canônico:

- Patrimônio;
- Investido;
- Resultado;
- Proventos;
- Rentabilidade desde o início;
- retorno mensal e diário;
- sinais negativos;
- consistência com Patrimônio e Rentabilidade.
