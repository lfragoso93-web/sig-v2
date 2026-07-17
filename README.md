# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 16/07/2026

O SGI v2 opera com arquitetura **DB-first**: dados de mercado, Tesouro Direto, Renda Fixa, proventos, benchmarks e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

A auditoria funcional das páginas **Resumo**, **Patrimônio** e **Rentabilidade** foi concluída. Os contratos monetários atuais usam o mesmo valuation canônico; performance histórica usa exclusivamente snapshots TWR; estados estimados, cobertura parcial e referências temporais são expostos ao usuário.

### Entrega consolidada

- Valuation canônico por classe de ativo.
- `summary.v2` e `rentabilidade.v2` validados em runtime.
- Snapshots patrimoniais diários com TWR diário, mensal e acumulado.
- Snapshots diários por classe para ativos com histórico persistido suportado.
- Renda Fixa valorizada por motor dedicado, sem lookup genérico de preços.
- Tesouro Direto com catálogo v2 e histórico oficial persistido.
- Histórico oficial da B3 via COTAHIST para ações, FIIs, ETFs nacionais e BDRs.
- Proventos líquidos recebidos agregados por competência de pagamento.
- Benchmarks CDI e IPCA servidos pelo backend a partir de séries persistidas.
- Reconciliação entre Resumo, Patrimônio, Rentabilidade, snapshots e classes.
- Atualização intradiária de preços a cada 90 minutos em dias úteis.
- `has_partial_prices`, `price_coverage_pct` e `return_is_estimated` explícitos.

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
        ├── fonte oficial do Tesouro: catálogo e histórico de títulos
        ├── SGS/BCB: CDI, Selic, IPCA e IGP-M
        ├── motor de Renda Fixa: contratos e indexadores
        └── provedores complementares: atualização recente e contingência
        ↓
asset_prices / rate_history / proventos
        ↓
Valuation canônico por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
TWR + reconciliação + cobertura
        ↓
summary.v2 / rentabilidade.v2 / posições canônicas
        ↓
Resumo, Patrimônio, Rentabilidade e demais módulos
```

Princípios:

- **DB-first:** páginas e snapshots não dependem de consultas externas realizadas pelo navegador.
- **Fonte oficial primeiro:** B3 e a fonte oficial do Tesouro sustentam o histórico doméstico.
- **Uma semântica financeira:** patrimônio, custo, resultado, proventos e TWR têm definições centralizadas.
- **Separação temporal:** valuation intradiário e performance fechada possuem referências independentes.
- **Idempotência:** rebuilds podem ser reexecutados sem duplicar registros.
- **Separação por classe:** mercado, Tesouro e Renda Fixa possuem motores próprios.
- **Qualidade explícita:** cobertura parcial, retorno estimado e indisponibilidade são informados.
- **Ausência não vira zero:** TWR indisponível é retornado como `null`, nunca como `0%` inventado.

---

## Páginas auditadas

### Resumo

- KPIs reconciliados com valuation, snapshots e proventos canônicos.
- Patrimônio intradiário separado de TWR fechado.
- Histórico mensal baseado no último snapshot de cada mês.
- Tabela de posições com variação diária separada de resultado acumulado.
- Contrato `summary.v2` estrito, com metadados de diagnóstico e cobertura.

### Patrimônio

- Cards alinhados ao mesmo contrato financeiro do Resumo.
- Histórico diário e mensal usando custo das posições abertas, não aportes acumulados.
- Fluxos externos preservados separadamente no tooltip.
- Período “Tudo” sem limite artificial.
- Distribuição por classe consumida do endpoint canônico.

### Rentabilidade

- Contrato `rentabilidade.v2` para KPIs monetários e TWR.
- TWR diário, mensal, 12 meses e desde o início composto a partir dos snapshots.
- TWR por classe para ações, FIIs, ETFs, BDRs, stocks e cripto quando materializado.
- Tesouro e Renda Fixa exibem valuation e resultado atuais sem promover retorno simples a TWR.
- CDI e IPCA lidos do banco; IBOV permanece indisponível até materialização persistida.
- Resultado por ativo derivado de posições e resultado realizado canônicos.
- Endpoint de reconciliação da página com tolerância monetária de R$ 0,01.

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

```bash
python -m app.cli.rebuild_b3_historical_market --start-year 2024 --end-year 2026
```

### Catálogo e histórico oficial do Tesouro

```bash
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

### Materialização de snapshots

```http
POST /performance/{portfolio_id}/evolution/backfill
```

O backfill reconstrói snapshots consolidados e snapshots por classe suportada.

---

## Funcionalidades implementadas

### Dados e valuation

- B3 COTAHIST como histórico primário para ativos brasileiros.
- Tesouro Direto com catálogo e histórico oficiais persistidos.
- Renda Fixa reconstruída por aplicação, indexador, vencimento e resgates.
- Câmbio histórico persistido para ativos internacionais.
- Auditoria de cobertura e ciclo de vida de negociação.
- Classificação `COMPLETE`, `PRE_LISTING`, `DELISTED`, `REAL_GAP` e `NO_HISTORY`.

### Proventos

- Dividendos, JCP, rendimentos e amortizações monetárias.
- Eventos não monetários fora dos totais financeiros.
- Somente eventos `RECEBIDO`, com valor líquido prioritário.
- Competência pela data de pagamento.
- Materialização por carteira conforme posição elegível.

### Importação CSV e eventos corporativos

- Preview, `dry_run`, validação linha a linha e mensagens em português.
- Resolução temporal de tickers antigos.
- Rebuild automático de snapshots após importações retroativas.
- Fundação para `TICKER_CHANGE` e futuros eventos corporativos.

---

## Pendências conhecidas

- #147 — corrigir alinhamento visual de perdas no gráfico da página Resumo.
- #148 — restaurar gráficos históricos por classe na página Patrimônio.
- #149 — implementar TWR diário dedicado para Tesouro Direto e Renda Fixa.
- #150 — materializar histórico persistido do IBOV.
- #151 — remover definitivamente o serviço legado de rentabilidade.

Essas pendências não alteram os contratos monetários já reconciliados; indisponibilidades são apresentadas explicitamente.

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
| `docs/CANONICAL_FINANCIAL_CONTRACT.md` | Contrato financeiro oficial do sistema |
| `docs/CANONICAL_MARKET_REBUILD_2026-07.md` | Consolidação da arquitetura de mercado |
| `ROADMAP.md` | Roadmap modular |
| `ROADMAP_SPRINTS.md` | Histórico de sprints |
| `CHANGELOG.md` | Histórico de mudanças |

---

## Próximos focos

1. Restaurar os gráficos históricos por classe da página Patrimônio (#148).
2. Implementar TWR dedicado de Tesouro e Renda Fixa (#149).
3. Materializar o benchmark IBOV no banco (#150).
4. Remover o serviço legado de rentabilidade (#151).
5. Corrigir o comportamento visual do gráfico divergente (#147).
6. Continuar Proventos, eventos corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.
