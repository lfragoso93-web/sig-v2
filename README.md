# SGI v2 — Sistema de Gestão de Investimentos

Plataforma pessoal para acompanhamento, consolidação e análise de investimentos.
Monorepo com backend FastAPI e frontend React + TypeScript.

A branch padrão de desenvolvimento é `stable-15jun`.

---

## Status atual — 14/07/2026

O SGI v2 está consolidando uma arquitetura **DB-first**: dados de mercado, proventos, benchmarks, Tesouro Direto e snapshots são persistidos antes de alimentar KPIs, páginas e gráficos. O objetivo é reduzir chamadas externas repetidas, tornar cálculos reprodutíveis e permitir auditoria por carteira, ativo e data.

### Entrega estrutural em validação

- Orquestrador oficial `full_market_rebuild` para manutenção completa.
- Auditoria de cobertura por ativo e identificação de lacunas históricas.
- Sincronização idempotente de preços apenas para intervalos faltantes.
- Metadados persistentes de provedor por ativo (`provider`, `provider_symbol`, `provider_status`, tentativas e último erro).
- Smart sync com estado `HISTORY_START_EXHAUSTED` para não repetir buscas antigas sem ganho.
- Snapshots TWR reconstruídos exclusivamente a partir do banco.
- Materialização de proventos em lotes seguros.
- Sanitização de preços anômalos antes da persistência.
- Tratamento dedicado para Tesouro Direto e classes sem cotação de mercado.
- Uso de histórico máximo suportado pelo provedor quando a lacuna é de início de série.

---

## Arquitetura resumida

```text
Importação CSV / lançamentos manuais
        ↓
Transações
        ↓
Catálogo de ativos
        ↓
Auditoria de cobertura
        ↓
Gap sync de preços e dados canônicos
        ↓
asset_prices / proventos / benchmarks / Tesouro
        ↓
Snapshots patrimoniais + TWR
        ↓
KPIs canônicos
        ↓
Resumo, Patrimônio, Rentabilidade e Dashboard
```

Princípios atuais:

- **DB-first:** cálculos de carteira leem dados persistidos; não consultam provedores externos durante snapshots.
- **Idempotência:** executar o rebuild novamente não deve duplicar registros nem repetir lacunas já esgotadas.
- **Sessões curtas:** chamadas externas acontecem fora de transações longas do banco.
- **Separação por classe:** ativos cotados, Tesouro Direto, Renda Fixa e cripto possuem regras próprias.
- **Qualidade explícita:** snapshots podem indicar `has_partial_prices` e `return_is_estimated` quando a cobertura não é completa.

---

## Comando oficial de manutenção

Para reconstruir a base canônica e recalcular snapshots:

```bash
python -m app.cli.full_market_rebuild
```

No Docker Compose:

```bash
docker compose exec backend python -m app.cli.full_market_rebuild
```

No PowerShell, salvando o log:

```powershell
$LogFile = ".\full-market-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

docker compose exec backend python -m app.cli.full_market_rebuild 2>&1 |
    Tee-Object -FilePath $LogFile
```

O comando executa, em ordem:

1. Reconciliação do catálogo e histórico de preços por lacunas.
2. Atualização de Tesouro Direto.
3. Atualização de benchmarks macroeconômicos.
4. Sincronização e materialização de proventos.
5. Reconstrução de snapshots TWR.
6. Auditoria final de cobertura.

---

## Funcionalidades implementadas

### Resumo, Patrimônio e Rentabilidade

- KPIs consolidados de patrimônio, investido, resultado, proventos e variação atual.
- Evolução diária e mensal com filtros de período.
- Distribuição por classe e metas de alocação.
- Variação diária por classe separada da rentabilidade acumulada.
- Ganho realizado e não realizado.
- Retorno diário, mensal, 12 meses e desde o início via cadeia TWR.
- Snapshots diários reconstruídos automaticamente após importações retroativas.

### Histórico de preços e dados canônicos

- Tabela `asset_prices` como fonte persistida para cálculo patrimonial.
- Auditoria de cobertura por ativo, data inicial necessária e última data disponível.
- Gap sync por borda faltante, com locks por ativo e concorrência controlada.
- Metadados persistentes para provedor, símbolo normalizado, status, tentativas e último erro.
- Histórico máximo para lacunas iniciais quando suportado pelo provedor.
- Validação contra preços nulos, negativos, infinitos ou anômalos.

### Proventos

- Dividendos, JCP, rendimentos, amortizações, bonificações e subscrições.
- Data Com, Data Ex e pagamento separados.
- Materialização por carteira conforme posição elegível.
- Histórico completo por ativo, com seed idempotente.
- Eventos não monetários fora dos totais financeiros.
- Processamento em lotes para evitar limites de parâmetros do driver de banco.

### Importação CSV

- Modelo oficial, preview, validação linha a linha e `dry_run`.
- Bloqueio enquanto existirem erros, avisos impeditivos ou falhas globais.
- Cards clicáveis para filtrar linhas válidas, avisos e erros.
- Resolução de tickers antigos com validação pela data da operação.
- Rebuild automático de snapshots e invalidação de caches financeiros.

### Eventos corporativos e aliases

- Modelo de aliases históricos de ativos.
- Detecção de renome de ticker via API v2.
- Evento corporativo `TICKER_CHANGE` idempotente por carteira.
- Conversão automática de saldo remanescente para o ticker atual.
- Preservação das compras e vendas históricas originais.
- Preparação para splits, grupamentos, bonificações, incorporações e conversões futuras.

### Conta e administração

- Login JWT com refresh token rotativo.
- Recuperação e alteração autenticada de senha.
- Carteiras isoladas por usuário.
- Criação, edição e exclusão segura de carteiras.
- Administração de usuários com edição de nome, papel e status.
- Proteção contra remoção do último superadmin.

---

## Stack tecnológica

### Backend

| Tecnologia | Uso |
|---|---|
| Python 3.12 | Linguagem base |
| FastAPI | API async |
| SQLAlchemy async | ORM |
| Alembic | Migrations |
| PostgreSQL | Banco de dados |
| Redis | Cache e locks |
| APScheduler | Jobs agendados |
| JWT | Autenticação |

### Frontend

| Tecnologia | Uso |
|---|---|
| React 19 | Interface |
| TypeScript | Tipagem |
| Vite | Build |
| TailwindCSS 4 | Estilos utilitários |
| Recharts | Gráficos |
| React Query | Estado servidor |
| Zustand | Estado global |
| Axios | Cliente HTTP |

---

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build
```

Para ambientes com múltiplas heads Alembic válidas, o entrypoint aplica `alembic upgrade heads`.

---

## Documentação

| Documento | Conteúdo |
|---|---|
| `docs/architecture.md` | Arquitetura DB-first, módulos e fluxos |
| `docs/price-history.md` | Histórico de preços, cobertura e gap sync |
| `docs/providers.md` | Papéis dos provedores, fallback e metadados |
| `docs/operations.md` | Comandos operacionais e validação local |
| `docs/snapshots.md` | Snapshots patrimoniais e TWR |
| `docs/canonical-data.md` | Dados canônicos e KPIs financeiros |
| `docs/rentabilidade.md` | Semântica dos cards e retorno TWR |
| `docs/CSV_IMPORT_PIPELINE.md` | Fluxo de validação, importação e rebuild |
| `docs/CORPORATE_ACTIONS.md` | Fundação do motor de eventos corporativos |
| `ROADMAP.md` | Roadmap modular atualizado |
| `ROADMAP_SPRINTS.md` | Histórico de sprints |
| `CHANGELOG.md` | Histórico de mudanças |

---

## Próximos focos

1. Finalizar resolução canônica de preços para mercado fracionário sem duplicar histórico.
2. Fazer snapshots de Tesouro consumirem o histórico dedicado da classe.
3. Revisar roteamento definitivo de cripto e Tesouro conforme cobertura documentada do provedor.
4. Ajustar visualmente os cards da página Rentabilidade.
5. Retomar bugs e inconsistências da página Resumo.
6. Avançar em Eventos Corporativos, Backup/Restore, OAuth, IRPF e Janela Global do Ativo.
