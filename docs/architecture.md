# Arquitetura — SGI v2

> Última atualização: 22/07/2026

Este documento descreve a arquitetura atual do SGI v2 após a consolidação do modelo **DB-first**, dos contratos financeiros canônicos e dos controles de reconstrução pré-produção.

## Objetivo

O sistema calcula patrimônio, resultado, proventos e rentabilidade com base em dados persistidos, versionados e auditáveis. Provedores externos preenchem o banco por jobs ou comandos operacionais; páginas, KPIs e snapshots não devem consultar provedores durante o cálculo financeiro.

## Fluxo financeiro principal

```text
CSV / lançamentos manuais
        ↓
transactions + fixed_income_investments + corporate_events
        ↓
catálogo canônico de ativos
        ↓
COTAHIST B3 | Tesouro oficial | séries macro | provedores normalizados
        ↓
asset_prices + rate_history + proventos canônicos
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + posições canônicas
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / demais módulos
```

## Princípios obrigatórios

### DB-first

Serviços financeiros leem dados persistidos. Chamadas externas pertencem a sincronizadores, jobs, adapters ou comandos de manutenção.

### Contrato financeiro único

`summary.v2` e `rentabilidade.v2` são as fontes oficiais de leitura financeira. O frontend valida esses contratos e não recompõe patrimônio, resultado ou rentabilidade localmente.

### Separação temporal

- valuation intradiário representa o estado atual da carteira;
- snapshots representam performance fechada em uma data;
- consolidado e classes só são reconciliados quando compartilham a mesma `snapshot_date`;
- ausência de TWR é representada por `null`, nunca por retorno simples.

### Idempotência

Reexecutar seed, sincronização, materialização ou rebuild deve produzir o mesmo estado lógico sem duplicar preços, proventos, posições ou snapshots.

### Qualidade explícita

Cobertura parcial, preços ausentes, retornos estimados, fonte e data de referência devem aparecer nos contratos. Ausência ou falha não pode ser convertida silenciosamente em zero.

### Conexões curtas

Chamadas HTTP não mantêm transações PostgreSQL abertas:

```text
ler estado mínimo
fechar sessão
consultar provedor
abrir sessão curta
persistir em lote
commit
```

## Módulos centrais

| Módulo | Responsabilidade |
|---|---|
| `transactions` | Fonte contábil das operações do usuário |
| `fixed_income_investments` | Aplicações e regras específicas de Renda Fixa |
| `corporate_events` | Fundação dos eventos que afetam identidade, quantidade e custo |
| `assets` | Catálogo canônico, aliases e metadados |
| `asset_prices` | Histórico diário persistido de preços |
| `rate_history` | Séries macroeconômicas persistidas |
| `asset_price_coverage_service` | Auditoria de cobertura por ativo |
| `asset_price_gap_sync_service` | Preenchimento de lacunas históricas |
| `dividend_*` | Eventos globais, elegibilidade e materialização por carteira |
| `treasury_price_history_service` | Histórico oficial dedicado do Tesouro Direto |
| valuation por classe | Patrimônio, custo e resultado atual por regra financeira específica |
| `portfolio_snapshot_twr_service` | Snapshots DB-only e cadeia TWR das classes suportadas |
| `full_market_rebuild_service` | Rebuild operacional de dados de mercado e snapshots |

## Proventos

O pipeline canônico separa:

1. descoberta do evento global;
2. persistência e normalização;
3. elegibilidade da carteira na data de corte;
4. materialização do direito;
5. reconhecimento financeiro pela data de pagamento.

Eventos não monetários permanecem rastreáveis, mas não entram nos agregados quando `is_cash=false`.

## Pré-produção e reconstrução

A reconstrução completa é diferente do `full_market_rebuild`. Ela protege dados de negócio antes de limpar dados reconstruíveis.

```text
pre-prod-inventory.v2
        ↓
pre-prod-backup.v3 + restore isolado
        ↓
pre-prod-cleanup-impact.v2
        ↓
pre-prod-export.v1
        ↓
limpeza controlada ainda pendente
        ↓
seeds canônicos
        ↓
reimportação da carteira
        ↓
rebuild de posições e snapshots
        ↓
reconciliação financeira final
```

### Classificação atual

- 11 tabelas preservadas;
- 3 tabelas exportadas antes da limpeza;
- 10 tabelas reconstruíveis;
- nenhuma tabela não classificada;
- nenhum achado bloqueante na validação real.

As tabelas exportáveis são `transactions`, `fixed_income_investments` e `corporate_events`.

### Garantias já consolidadas

- inventário e exportação somente leitura;
- backup e inventário no mesmo snapshot `REPEATABLE READ READ ONLY`;
- checksum SHA-256;
- restore apenas em banco vazio e isolado;
- gate de foreign keys e ciclos;
- artefatos versionados e sem sobrescrita;
- normalização de `ordinal_position` na projeção CSV;
- zero escritas na origem durante inventário, backup, impacto e exportação.

## Scheduler diário

A dependência lógica deve ser preservada:

```text
sincronizar catálogo e preços
        ↓
atualizar Tesouro e benchmarks
        ↓
sincronizar e materializar proventos
        ↓
reconstruir snapshots
        ↓
servir KPIs canônicos
```

## Tipos de ativos

| Classe | Tratamento |
|---|---|
| Ações, ETFs nacionais e BDRs | Histórico em `asset_prices`, prioritariamente B3 COTAHIST |
| FIIs | Histórico persistido e coleta específica de proventos |
| Stocks e ETFs internacionais | Adapter internacional com fallback controlado |
| Cripto | Histórico persistido; roteamento definitivo ainda pendente |
| Tesouro Direto | Catálogo, preços e valuation dedicados |
| Renda Fixa | Motor de accrual/indexador, sem cotação genérica |

## Pendências arquiteturais conhecidas

1. Implementar a limpeza executável e concluir o rebuild pré-produção (#158).
2. Remover o serviço legado de rentabilidade e caches obsoletos (#151).
3. Materializar o histórico persistido do IBOV (#150).
4. Implementar TWR diário dedicado, separando Tesouro e Renda Fixa (#149).
5. Consolidar o motor de eventos corporativos independente do fornecedor (#129).
6. Evoluir adapters brapi v2 sem expor payloads de fornecedor ao domínio (#130).
7. Consolidar provider registry por capacidade antes da configuração dinâmica (#127).
8. Migrar timestamps UTC legados para objetos timezone-aware (#192).
9. Evoluir locks em memória para locks distribuídos antes de múltiplas réplicas.