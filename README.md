# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos, com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`. A promoção para `main` ocorre por PR após validação e atualização da documentação viva.

## Status atual — 17/07/2026

O SGI v2 opera com arquitetura **DB-first**: catálogo, preços, taxas, proventos e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos.

### Entregas consolidadas

- Valuation canônico por classe de ativo.
- Contratos `summary.v2` e `rentabilidade.v2` validados em runtime.
- Snapshots patrimoniais diários, mensais e por classe suportada.
- Histórico oficial da B3 via COTAHIST.
- Tesouro Direto com catálogo canônico, ano comercial de RendA+/Educa+ e preços oficiais persistidos.
- Renda Fixa valorizada por motor dedicado.
- CDI e IPCA servidos a partir de séries persistidas.
- Proventos monetários líquidos agregados por data de pagamento.
- Reconciliação entre Resumo, Patrimônio, Rentabilidade e snapshots.
- Cobertura parcial e retornos estimados explicitados no contrato.

### Tesouro Direto — Blocos 3.1 e 3.2

O fluxo usado pela página Resumo foi alinhado ao pipeline canônico:

- BRAPI como fonte primária de preço recente;
- Tesouro Transparente como fallback oficial;
- último preço persistido como contingência;
- resolução case-insensitive de tickers e aliases;
- preço devolvido pelo ticker original da posição;
- criação automática de ativos duplicados bloqueada;
- regressões para RendA+ adicionadas.

Os valores atuais de Selic e RendA+ foram validados na interface. A limpeza integral da base foi adiada para o checklist pré-produção e está registrada na issue #158.

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo canônico de ativos
        ↓
B3 COTAHIST | Tesouro Transparente | SGS/BCB | motores dedicados
        ↓
asset_prices / rate_history / proventos
        ↓
Valuation canônico por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 / rentabilidade.v2 / posições canônicas
        ↓
Resumo, Patrimônio, Rentabilidade e demais módulos
```

Princípios: DB-first, fonte oficial primeiro, idempotência, ausência não convertida em zero, separação entre valuation intradiário e performance fechada e contratos financeiros únicos.

## Comandos operacionais

```bash
python -m app.cli.full_market_rebuild
python -m app.cli.rebuild_b3_historical_market
python -m app.cli.sync_treasury_catalog_v2
python -m app.cli.rebuild_treasury_official_prices
```

## Prioridades atuais

1. Página Resumo: KPIs, variação versus rentabilidade, dropdowns e consistência visual.
2. Proventos: cobertura por classe, materialização e diagnósticos.
3. Patrimônio: restaurar gráficos históricos por classe (#148).
4. Rentabilidade: TWR dedicado para Tesouro e Renda Fixa (#149) e IBOV persistido (#150).
5. Remover o serviço legado de rentabilidade (#151).
6. Corrigir o gráfico divergente da página Resumo (#147).
7. Validar dependências pendentes do Dependabot (#159).
8. Executar rebuild limpo da base antes do go-live (#158).

## Dependências

Atualizações já auditadas e incorporadas à `stable-15jun`:

- react-hook-form 7.81.0;
- Recharts 3.9.2;
- aiosqlite 0.22.1;
- Uvicorn 0.51.0;
- redis-py 8.0.1.

Pendentes de validação isolada: build-tools/TypeScript 7, ESLint stack, httpx 0.28.1 e mypy 2.2.0. O acompanhamento oficial está na issue #159.

## Pré-produção

A primeira entrada em produção exige:

1. backup validado;
2. limpeza controlada de dados reconstruíveis;
3. seed B3 COTAHIST;
4. seed Tesouro Transparente;
5. seed de benchmarks e proventos;
6. importação CSV completa da carteira;
7. rebuild de posições e snapshots;
8. reconciliação financeira e auditoria de cobertura.

Checklist completo: issue #158.

## Stack

Backend: Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis e APScheduler.

Frontend: React 19, TypeScript, Vite, TailwindCSS 4, Recharts, React Query, Zustand e Axios.

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

## Documentação viva

- `ROADMAP.md` — prioridades e andamento modular.
- `ROADMAP_SPRINTS.md` — histórico de sprints.
- `CHANGELOG.md` — mudanças relevantes.
- `docs/architecture.md` — arquitetura DB-first.
- `docs/providers.md` — fontes e fallbacks.
- `docs/operations.md` — operação e rebuilds.
- `docs/CANONICAL_FINANCIAL_CONTRACT.md` — contrato financeiro oficial.
