# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 16/07/2026

O SGI v2 opera com arquitetura **DB-first**: dados de mercado, Tesouro Direto, Renda Fixa, proventos, benchmarks e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

### Entrega estrutural consolidada

- Valuation canônico por classe de ativo.
- Snapshots diários com TWR diário, mensal e acumulado desde o início.
- Renda Fixa valorizada por motor dedicado, sem lookup genérico de preços.
- Tesouro Direto com catálogo v2 e histórico oficial do Tesouro Transparente.
- RendA+ e Educa+ normalizados pelo ano comercial.
- Histórico oficial da B3 via COTAHIST para ações, FIIs, ETFs nacionais e BDRs.
- Carga B3 validada com 2.258 ativos e 984.949 preços entre 2024 e 2026.
- Ciclo de negociação consciente de pré-listagem, deslistagem e lacunas reais.
- `has_partial_prices` e `return_is_estimated` calculados pela cobertura real.
- `full_market_rebuild` como orquestrador operacional oficial.

---

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo canônico de ativos
        ↓
Fontes oficiais e complementares
        ├── B3 COTAHIST: histórico de renda variável brasileira
        ├── Tesouro Transparente: catálogo e histórico do Tesouro
        ├── motor de Renda Fixa: contratos e indexadores
        └── provedores complementares: atualização recente e contingência
        ↓
asset_prices / proventos / benchmarks
        ↓
Valuation canônico por classe
        ↓
Snapshots patrimoniais + TWR
        ↓
KPIs canônicos
        ↓
Resumo, Patrimônio, Rentabilidade e Dashboard
```

Princípios:

- **DB-first:** snapshots não consultam APIs externas.
- **Fonte oficial primeiro:** B3 e Tesouro Transparente sustentam o histórico doméstico.
- **Idempotência:** rebuilds podem ser reexecutados sem duplicar registros.
- **Separação por classe:** mercado, Tesouro e Renda Fixa possuem motores próprios.
- **Qualidade explícita:** cobertura parcial e retorno estimado são persistidos no snapshot.
- **Pré-listagem não é erro:** antes da primeira cotação oficial, o custo da posição é usado sem marcar lacuna.

---

## Comandos operacionais

### Rebuild completo

```bash
python -m app.cli.full_market_rebuild
```

```powershell
$LogFile = ".\full-market-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
docker compose exec backend python -m app.cli.full_market_rebuild 2>&1 |
    Tee-Object -FilePath $LogFile
```

### Histórico oficial da B3

```bash
python -m app.cli.rebuild_b3_historical_market
```

Exemplo por intervalo:

```bash
python -m app.cli.rebuild_b3_historical_market --start-year 2024 --end-year 2026
```

### Catálogo e histórico oficial do Tesouro

```bash
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

---

## Funcionalidades implementadas

### Resumo, Patrimônio e Rentabilidade

- KPIs consolidados de patrimônio, investido, resultado, proventos e variação atual.
- Resultado separado de rentabilidade percentual.
- Resultado composto por ganho realizado, ganho não realizado e proventos.
- Retorno diário, mensal, 12 meses e desde o início via cadeia TWR.
- Evolução diária e mensal com snapshots reconstruíveis.
- Indicadores de cobertura real por snapshot.

### Histórico de preços

- `asset_prices` como fonte persistida para cálculo patrimonial.
- B3 COTAHIST como histórico primário para ativos brasileiros.
- Auditoria de cobertura por ativo e data.
- Gap sync idempotente para complementos recentes.
- Preservação de ativos deslistados.
- Classificação de `COMPLETE`, `PRE_LISTING`, `DELISTED`, `REAL_GAP` e `NO_HISTORY`.

### Tesouro Direto

- Catálogo oficial orientado pelo Tesouro Transparente.
- Histórico oficial persistido em `asset_prices`.
- Brapi como fallback secundário.
- Aliases legados deduplicados sem apagar transações.
- RendA+ e Educa+ resolvidos pelo ano comercial.
- Snapshots consumindo preços oficiais, sem fallback por preço médio quando há cobertura.

### Renda Fixa

- Contratos reconstruídos por aplicação e resgate.
- Valorização por indexadores e regras dedicadas.
- Principal, valor corrigido e rendimento expostos no rebuild.
- Classe removida do lookup genérico de cotações.

### Proventos

- Dividendos, JCP, rendimentos, amortizações, bonificações e subscrições.
- Data Com, Data Ex e pagamento separados.
- Materialização por carteira conforme posição elegível.
- Eventos não monetários fora dos totais financeiros.

### Importação CSV e eventos corporativos

- Preview, `dry_run`, validação linha a linha e mensagens em português.
- Resolução temporal de tickers antigos.
- Rebuild automático de snapshots após importações retroativas.
- Fundação para `TICKER_CHANGE` e futuros eventos corporativos.

---

## Stack tecnológica

### Backend

Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e APScheduler.

### Frontend

React 19, TypeScript, Vite, TailwindCSS 4, Recharts, React Query, Zustand e Axios.

---

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

---

## Documentação

| Documento | Conteúdo |
|---|---|
| `docs/architecture.md` | Arquitetura DB-first, módulos e fluxos |
| `docs/price-history.md` | Histórico de preços, cobertura e gap sync |
| `docs/providers.md` | Papéis das fontes e fallbacks |
| `docs/operations.md` | Comandos operacionais |
| `docs/snapshots.md` | Snapshots patrimoniais e TWR |
| `docs/canonical-data.md` | Dados canônicos e KPIs financeiros |
| `docs/rentabilidade.md` | Semântica de retorno e resultado |
| `docs/CANONICAL_MARKET_REBUILD_2026-07.md` | Consolidação desta entrega estrutural |
| `ROADMAP.md` | Roadmap modular |
| `ROADMAP_SPRINTS.md` | Histórico de sprints |
| `CHANGELOG.md` | Histórico de mudanças |

---

## Próximos focos

1. Auditar os cards da página Resumo contra os snapshots canônicos.
2. Confirmar Resultado incluindo todos os proventos materializados.
3. Revisar a apresentação visual de Rentabilidade e indicadores de qualidade.
4. Integrar o rebuild histórico B3 ao fluxo operacional completo após validação final.
5. Avançar em eventos corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.
