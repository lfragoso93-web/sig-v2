# Histórico de preços e gap sync

> Última atualização: 14/07/2026

Este documento descreve como o SGI v2 coleta, valida, persiste e consome histórico de preços.

---

## Regra principal

Snapshots e KPIs não consultam provedores externos. Eles leem somente `asset_prices` e demais tabelas canônicas.

```text
Provedor externo
        ↓
Sincronização de lacunas
        ↓
asset_prices
        ↓
Snapshots / KPIs / telas
```

---

## Tabela `asset_prices`

Armazena o preço diário por ativo.

Campos relevantes:

- `asset_id`
- `timestamp`
- `close`
- `source`

A unicidade é por:

```text
asset_id + timestamp
```

A persistência usa upsert idempotente para evitar duplicidade.

---

## Metadados no ativo

A tabela `assets` possui metadados operacionais para reduzir chamadas externas repetidas:

| Campo | Uso |
|---|---|
| `provider` | Fonte preferencial ou última fonte usada |
| `provider_symbol` | Símbolo normalizado para o provedor |
| `provider_status` | Estado da última sincronização |
| `provider_last_sync_at` | Data/hora da última tentativa |
| `provider_last_error` | Último erro relevante |
| `provider_attempts` | Quantidade acumulada de tentativas |

Estados principais:

- `OK`
- `PENDING`
- `FAILED`
- `HISTORY_START_EXHAUSTED`

---

## Auditoria de cobertura

O serviço `asset_price_coverage_service` cruza:

- ativos do catálogo;
- transações;
- preços persistidos;
- data inicial necessária;
- data final necessária.

A auditoria produz:

```json
{
  "ticker": "EXEMPLO3",
  "required_from": "2024-01-01",
  "required_to": "2026-07-14",
  "first_price_date": "2024-01-02",
  "last_price_date": "2026-07-13",
  "status": "COMPLETE",
  "needs_sync": false,
  "missing_ranges": []
}
```

Quando há lacunas:

```json
{
  "ticker": "EXEMPLO4",
  "status": "PARTIAL_BOTH",
  "needs_sync": true,
  "missing_ranges": [
    {"date_from": "1900-01-01", "date_to": "2020-01-10", "reason": "missing_start"},
    {"date_from": "2026-07-01", "date_to": "2026-07-14", "reason": "stale_end"}
  ]
}
```

---

## Gap sync

O serviço `asset_price_gap_sync_service` executa apenas os intervalos indicados pela auditoria.

Garantias:

- lock por `asset_id`;
- sessão curta para leitura;
- chamadas externas sem conexão do banco presa;
- sessão curta para persistência;
- upsert idempotente;
- validação de preços antes de gravar.

---

## Histórico máximo

Para lacunas no início da série, o SGI usa a maior janela suportada pelo provedor.

Exemplos conceituais:

```text
required_from=1900-01-01
reason=missing_start
        ↓
solicitar histórico máximo
        ↓
filtrar o intervalo retornado
```

Para fonte internacional via biblioteca de mercado, a chamada usa `period=max`, não uma data artificial de 1900.

Para a fonte principal de ações/BDRs/ETFs nacionais, o histórico máximo é solicitado quando suportado pela rota.

FIIs continuam com janela explícita quando a rota documentada não oferece `range=max`.

---

## Validação de preços

Antes de persistir, o sistema rejeita:

- `None`;
- zero;
- negativos;
- `NaN`;
- infinito;
- preços unitários absurdamente altos para a escala do banco.

O objetivo é evitar que dados corrompidos de ajuste, grupamento ou fonte externa derrubem a sincronização.

Registros inválidos são resumidos por ativo e fonte para não poluir os logs.

---

## Mercado fracionário

O ticker contábil pode ser fracionário, por exemplo:

```text
EXEMPLO3F
```

O símbolo de provedor deve apontar para o ativo-base:

```text
EXEMPLO3F → EXEMPLO3
```

Estado atual:

- o ticker contábil é preservado;
- o `provider_symbol` já é normalizado;
- ainda falta evitar duplicação física do histórico usando um `pricing_asset_id` ou alias canônico.

---

## Classes sem cotação genérica

Algumas classes não passam pelo pipeline genérico de `asset_prices`:

| Classe | Tratamento |
|---|---|
| Renda Fixa | Motor interno de correção |
| Tesouro Direto | Serviço dedicado |
| Ativos sem cotação | `NO_MARKET_QUOTE` |

---

## Full rebuild

O comando oficial:

```bash
python -m app.cli.full_market_rebuild
```

executa a auditoria e o gap sync antes de reconstruir snapshots.

---

## Métricas esperadas

Relatórios de manutenção devem mostrar:

- ativos auditados;
- ativos solicitados;
- registros recebidos;
- registros inseridos;
- erros;
- ignorados;
- distribuição por status.

Um rebuild saudável deve reduzir progressivamente:

- `MISSING`;
- `STALE`;
- `PARTIAL_BOTH`;
- chamadas para lacunas já esgotadas.
