# Correção de Proventos: Data Com Econômica e Resolução de Aliases de Ativos

> Data: 29/10/2026  
> Escopo: Proventos de Carteira, Catálogo Global e Drawer de Detalhes  
> Arquivos: `canonical_dividend_entitlement.py`, `canonical_dividend_entitlement_reader.py`, `proventos_service.py`, `AssetDetailDrawer.tsx`

---

## 1. Problema Identificado

No ambiente de produção, ativos em carteira (ex.: ETF `AREA11`) exibiam normalmente seu histórico de proventos declarados no modal de detalhes do ativo (aba *Fundamentos*), porém não constavam na página **Proventos** da carteira (`/portfolios/{id}/proventos`), não exibiam valores recebidos ou a receber e não integravam a série histórica mensal ou o gráfico de distribuição.

Adicionalmente, o modal de detalhes do ETF exibia a mensagem contraditória *"Política de Proventos: Reinvestimento Automático de Proventos (Este ETF não distribui proventos em conta...)"* mesmo quando o ativo possuía proventos declarados e distribuídos aos cotistas.

---

## 2. Diagnóstico e Causa Raiz

1. **Ausência de `record_date` em Eventos Globais do Yahoo Finance:**
   Mais de 53% dos eventos em `asset_dividends` (mais de 22.000 registros na base) foram alimentados pelo provedor Yahoo Finance (`yfinance_history`), que disponibiliza exclusivamente a `ex_date` (Data Ex), deixando `record_date` nulo. O serviço `canonical_dividend_entitlement.py` descartava sumariamente qualquer evento com `record_date IS NULL` sob o motivo `AMBIGUOUS_ENTITLEMENT_DATE`, omitindo proventos legítimos de cotistas com posições antigas.
2. **Divergência de Aliases de Tipo (`ETF` vs `ETF_NACIONAL`):**
   Na tabela `assets`, o tipo é cadastrado como `ETF_NACIONAL`, enquanto na tabela `asset_dividends` ou nos filtros da UI o tipo pode ser consultado como `ETF`. A ausência de normalização impedia a reconciliação precisa com as transações em carteira e afetava filtros específicos.
3. **Texto Estático no Drawer de Ativos:**
   O componente `AssetDetailDrawer.tsx` utilizava fallback estático para `"Reinvestimento Automático de Proventos"` sempre que `etf.dividend_policy` era nulo, ignorando a existência de `dividend_history`.

---

## 3. Correções Aplicadas

1. **Data Com Econômica Canônica (`canonical_dividend_entitlement.py`):**
   - Implementado cálculo de dia útil anterior (`previous_business_day`) e resolução da data efetiva de direito (`effective_entitlement_date`).
   - Quando `record_date` estiver ausente, adota-se o dia útil imediatamente anterior à `ex_date`.
   - **Garantia Anti-Leak:** Compras feitas na Data Ex ou posteriormente continuam com posição elegível zero (`NO_POSITION`), impedindo qualquer vazamento indevido de direitos a compradores ex-dividendo.
   - Eventos sem nenhuma das duas datas continuam sendo classificados de forma segura como `AMBIGUOUS_ENTITLEMENT_DATE`.
2. **Normalização Bidirecional de Aliases (`canonical_dividend_entitlement_reader.py` e `proventos_service.py`):**
   - Mapeamento explícito de sinônimos (`ETF` $\leftrightarrow$ `ETF_NACIONAL`, etc.).
   - Utilização de `normalize_asset_type` na leitura SQL, no agrupamento de movimentações em memória e nos filtros da API pública de proventos.
3. **Correção Visual no Drawer de Ativos (`AssetDetailDrawer.tsx`):**
   - Se `dividendHistory.length > 0`, a política é exibida como `"Distribuição Periódica de Proventos"`, descrevendo adequadamente o repasse periódico aos cotistas.

---

## 4. Validação

- 72 testes de proventos e dividendos backend aprovados (`pytest`).
- 258 testes de frontend aprovados (`vitest`).
- Architecture Doctor com static checks aprovados (`exit_code=0`).
