# PLANO DE AÇÃO EXECUTÁVEL — SGI v2

**Data:** 02 de Julho de 2026  
**Duração Estimada:** 8-12 semanas  
**Equipe Recomendada:** 2 devs (1 backend, 1 frontend) + 1 QA part-time

---

## 📊 Visão Geral dos Gaps

**Total:** 21 gaps identificados  
**Esforço Total:** ~120-150 horas  
**Status:** 78% de completude funcional

```
Criticidade:  🔴 4 CRÍTICOS | 🟡 13 MÉDIOS | 🟢 4 BAIXOS
Categoria:    6 áreas (Performance, Frontend, Features, Testes, Docs, Segurança)
```

📖 **Referência Completa:** `GAPS_ANALISE_COMPLETA.md`

---

## 🎯 SPRINT 1: Produção-Ready (Semana 1-2) — 30-40h

### Objetivo
Tornar aplicativo seguro, performático e pronto para produção imediata.

### Tarefas (Em Ordem de Execução)

#### 1.1 🔴 Corrigir Índices PostgreSQL (2h)
**Status:** ❌ NÃO INICIADO  
**Arquivos:** 
- `backend/alembic/versions/024_add_additional_indexes.py` ← JÁ EXISTE (apenas indexes de dividends)
- Precisa criar: `025_add_performance_indexes.py`

**O que fazer:**
```bash
# Criar nova migration
cd backend
alembic revision -m "add performance indexes"

# Adicionar ao arquivo gerado:
CREATE INDEX CONCURRENTLY idx_tx_portfolio_date 
  ON transactions (portfolio_id, date ASC);

CREATE INDEX CONCURRENTLY idx_price_history_ticker_date 
  ON price_history (ticker, date DESC);

CREATE INDEX CONCURRENTLY idx_portfolio_snapshot_portfolio_date 
  ON portfolio_snapshot (portfolio_id, snapshot_date DESC);

CREATE INDEX CONCURRENTLY idx_fx_rates_date 
  ON fx_rates (rate_date DESC);
```

**Impacto:** -30-50% latência em queries críticas  
**Teste:** `EXPLAIN ANALYZE` em 3 queries principais (vide doc)

---

#### 1.2 🔴 Ativar Monitoramento de Queries (1h)
**Status:** ❌ NÃO INICIADO  
**Arquivo:** `docker-compose.yml`

**O que fazer:**
```yaml
postgresql:
  environment:
    - log_min_duration_statement=100  # loga queries > 100ms
    - shared_preload_libraries=pg_stat_statements
    - log_connections=on
```

**Teste:** `SELECT query, calls, mean_exec_time FROM pg_stat_statements`

---

#### 1.3 🟡 Completar Cache Redis (2-3h)
**Status:** ⚠️ PARCIAL (só tem cache em rentabilidade)  
**Arquivo:** `backend/app/services/portfolio_service.py`

**O que fazer:**
```python
# Decorador já existe em rentabilidade_service.py
# Adicionar em portfolio_service.py:

@cache_key("portfolio", portfolio_id, "summary", ttl=120)
async def get_portfolio_summary(db, portfolio_id):
    # ... implementação existente
    
@cache_key("portfolio", portfolio_id, "positions", ttl=120)
async def get_portfolio_positions(db, portfolio_id):
    # ... implementação existente

# Invalidar cache em transaction_service quando nova transação criada
```

**Teste:** Redis hitrate deve aumentar 50%+ em 2 min

---

#### 1.4 🟢 Sprint 6A: Remover Referências a APIs Externas (2h)
**Status:** ❌ NÃO INICIADO (Planejado mas não feito)  
**Arquivos:**
- `README.md` — remover nomes: BRAPI, YFinance, Alpha Vantage
- `backend/app/main.py` — descrições de endpoints
- `.env.example` — comentários
- `CHANGELOG.md` — histórico

**O que fazer:**
```python
# Em main.py, mudar:
"Integração com BRAPI para cotações"
# Para:
"Integração com provedor de cotações"

# Em .env.example:
# BRAPI_TOKEN=seu_token_aqui  # Provedor de cotações brasileiro
# ALPHA_VANTAGE_API_KEY=...   # Provedor de dados internacionais
```

**Teste:** Varrer codebase com grep para "BRAPI\|YFinance\|Alpha"

---

#### 1.5 🟡 Setup de Testes Frontend (4-5h)
**Status:** ❌ NÃO INICIADO (0% cobertura)  
**Arquivo:** `frontend/`

**O que fazer:**
```bash
cd frontend

# 1. Instalar dependências
npm install -D vitest @testing-library/react @testing-library/dom jsdom

# 2. Criar vitest.config.ts
cat > vitest.config.ts << 'EOF'
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
EOF

# 3. Criar arquivo setup
mkdir -p src/test
cat > src/test/setup.ts << 'EOF'
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
afterEach(() => cleanup());
EOF

# 4. Adicionar a package.json:
"test": "vitest",
"test:coverage": "vitest --coverage",
"test:watch": "vitest --watch"

# 5. Criar primeiro teste (exemplo)
mkdir -p src/components/ui/__tests__
cat > src/components/ui/__tests__/KpiCard.test.tsx << 'EOF'
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import KpiCard from '../KpiCard';

describe('KpiCard', () => {
  it('renders title and value', () => {
    render(<KpiCard title="Total" value="R$ 100.000" change={5} />);
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('R$ 100.000')).toBeInTheDocument();
  });
});
EOF

# 6. Rodar testes
npm test
```

**Saída esperada:** ✅ Primeiro teste passando

---

#### 1.6 🟡 Verificar N+1 Fixes (1h)
**Status:** ⚠️ JÁ IMPLEMENTADO (vide QUERY_OPTIMIZATION.md)  
**Verificar:**
```bash
# Em backend/app/services/:
grep -n "_calc_totals" portfolio_snapshot_service.py  # Deve ter batch prefetch
grep -n "sum_dividends" portfolio_service.py          # Deve ter single query
grep -n "_calc_invested_up_to_both" rentabilidade_service.py  # Dual query
```

**Se tudo OK:** ✅ Skip esta tarefa

---

### Checklist Sprint 1

- [ ] 1.1 — Índices PostgreSQL aplicados + EXPLAIN ANALYZE OK
- [ ] 1.2 — Monitoramento habilitado, logs de query lentas aparecendo
- [ ] 1.3 — Cache Redis funcional em `/resumo` e `/posicoes`
- [ ] 1.4 — Grep retorna 0 ocorrências de nomes de APIs externas em docs
- [ ] 1.5 — `npm test` passa com pelo menos 5 testes frontend
- [ ] 1.6 — N+1 fixes verificados ou já OK

**Saída esperada:** App pronto para staging/produção com performance baseline

---

## 🎯 SPRINT 2: Features Críticas (Semana 3-4) — 40-60h

### Objetivo
Implementar features planejadas que estão 100% faltando.

### Tarefas (Por Prioridade)

#### 2.1 🔴 CSV Import de Ativos (12-15h)
**Status:** ❌ NÃO INICIADO (Sprint 6D planejada mas nunca feita)

**Escopo:**
- ✅ Backend: `GET /api/v1/assets/csv-template` + `POST /api/v1/portfolios/{id}/import-csv`
- ✅ Frontend: Modal com preview + confirmação
- ✅ Validação linha-a-linha com relatório de erros
- ✅ Importação atômica (tudo ou rollback)

**Arquivos a criar/modificar:**
```python
# backend/app/routers/portfolios.py
@router.get("/{portfolio_id}/csv-template")
async def get_csv_template():
    """Retorna template CSV para download"""

@router.post("/{portfolio_id}/import-csv")
async def import_csv(portfolio_id: int, file: UploadFile):
    """Importa transações em massa com validação"""
    
# backend/app/services/csv_import_service.py (novo)
class CSVImportService:
    async def validate_and_import(...)
    async def generate_template(...)
```

```typescript
// frontend/src/components/ImportCSVModal.tsx (novo)
export const ImportCSVModal = ({ portfolioId }) => {
  // Preview de linhas
  // Validação em tempo real
  // Confirmação antes de importar
}

// frontend/src/pages/Transacoes.tsx
// Adicionar botão "Importar CSV"
```

**Teste:** 
```bash
# Criar CSV com 10 linhas
# Importar com 1 erro (linha inválida)
# Verificar que apenas 9 linhas foram importadas
# Relatório mostra erro na linha X
```

---

#### 2.2 🔴 Backup & Restore do Banco (12-15h)
**Status:** ❌ NÃO INICIADO (Sprint 10B planejada mas nunca feita)

**Escopo:**
- ✅ Backend: `POST /admin/database/backup` + `POST /admin/database/restore`
- ✅ Frontend: Painel admin com botões
- ✅ Autenticação dupla (senha + confirmação)
- ✅ Backup armazenado em volume com TTL 24h

**Arquivos a criar:**
```python
# backend/app/routers/admin.py (adicionar)
@router.post("/database/backup")
async def backup_database(current_user = Depends(require_superadmin)):
    """Gera dump PostgreSQL para download"""
    
@router.post("/database/restore")
async def restore_database(file: UploadFile, password: str):
    """Restaura banco de arquivo de backup"""
    
# backend/app/services/backup_service.py (novo)
async def backup_database() -> bytes
async def restore_database(backup_file: bytes) -> None
```

```typescript
// frontend/src/components/admin/BackupPanel.tsx (novo)
// Botões: Fazer Backup, Restaurar Backup
// Modal de confirmação com aviso de downtime
```

**Teste:**
```bash
# Fazer backup
# Corromper 1 registro no DB
# Restaurar backup
# Verificar que registro foi recuperado
```

---

#### 2.3 🟡 Completar IRPF (10-12h)
**Status:** ⚠️ PARCIAL (interface + backend existem, lógica incompleta)

**O que está faltando:**
- Exportação PDF/CSV de relatório
- Cálculo consolidado por ano-calendário
- Isenção para vendas até R$20.000/mês
- Apuração Day Trade vs Swing Trade
- Testes de validação

**Arquivos:**
```python
# backend/app/services/irpf_service.py (expandir)
async def get_irpf_report_by_year(portfolio_id, year):
    """Retorna relatório completo do ano"""
    # Consolidar por ano-calendário
    # Aplicar isenção de R$ 20k/mês
    
async def calculate_daytrade_vs_swingtrade(transactions):
    """Classifica trades por horizonte"""
    
# backend/app/routers/irpf.py (adicionar)
@router.get("/report/{year}/pdf")
async def export_irpf_pdf(portfolio_id, year):
    """Exporta em PDF"""
```

```typescript
// frontend/src/pages/IRPFPage.tsx (expandir)
// Seletor de ano
// Filtros por mês/classe/tipo de trade
// Botões: Download PDF, Download CSV
// Tabela com cálculos mês a mês
```

**Teste:**
```bash
# Criar 5 transações de venda (R$ 5k cada = R$ 25k no mês)
# Verificar que isenção foi aplicada (apenas R$ 5k tributável)
# Exportar PDF e verificar formatação
```

---

#### 2.4 🟡 Audit Logs (8-10h)
**Status:** ❌ NÃO INICIADO (Sprint 7B planejada)

**Escopo:**
- ✅ Modelo `AuditLog` (user_id, action, resource, timestamp, metadata JSON)
- ✅ Middleware para captura automática
- ✅ Endpoint `GET /admin/users/{id}/audit`
- ✅ Exportação CSV
- ✅ Tela de auditoria no admin

**Arquivos:**
```python
# backend/app/models/audit_log.py (novo)
class AuditLog(Base):
    user_id: int
    action: str
    resource: str
    timestamp: datetime
    metadata: dict
    
# backend/app/middleware/audit_middleware.py (novo)
async def audit_middleware(request, call_next):
    # Intercepta POST/PUT/DELETE
    # Registra em AuditLog
    
# backend/alembic/versions/026_create_audit_log_table.py (novo)
```

---

#### 2.5 🟡 AssetDetailDrawer (8-10h)
**Status:** ❌ NÃO INICIADO (Sprint 9 planejada)

**Escopo:**
- ✅ Componente drawer que abre ao clicar em ativo
- ✅ Gráfico de preço histórico (OHLCV)
- ✅ Histórico de proventos
- ✅ Dividend Yield (DY) calculado
- ✅ Disponível em PatrimonioPage, Transacoes, RentabilidadePage

**Arquivos:**
```typescript
// frontend/src/components/AssetDetailDrawer.tsx (novo)
export const AssetDetailDrawer = ({ ticker, isOpen, onClose }) => {
  // Gráfico de preço
  // Tabela de proventos
  // KPIs: DY, P/L, Quantidade
}

// frontend/src/pages/PatrimonioPage.tsx (modificar)
// Tornar linhas da tabela clicáveis → abre drawer
// Mesmo para RentabilidadePage.tsx
```

**Teste:**
```bash
# Clicar em linha de ativo
# Drawer abre com gráfico
# Verificar dados estão corretos
```

---

### Checklist Sprint 2

- [ ] 2.1 — CSV import funcional com validação
- [ ] 2.2 — Backup/restore funcional (teste de recuperação OK)
- [ ] 2.3 — IRPF exporta PDF com cálculos corretos
- [ ] 2.4 — Audit logs sendo registrados para todas as ações
- [ ] 2.5 — Drawer abre ao clicar em ativo com dados corretos

**Saída esperada:** Todas as features planejadas (roadmap) implementadas

---

## 🎯 SPRINT 3: Qualidade & UX (Semana 5-7) — 40-50h

### Objetivo
Melhorar cobertura de testes, documentação, e experiência do usuário.

### Tarefas

#### 3.1 🟡 Expandir Testes Backend (15-20h)
**Status:** ⚠️ PARCIAL (8 testes existem, faltam 40+)

**Adicionar testes para:**
- ✅ Todos os routers (admin, assets, class_targets, fixed_income, goals, irpf, treasury)
- ✅ Services sem cobertura (irpf_service, treasury_service, goals_service)
- ✅ Fluxos críticos: login → transação → rentabilidade

**Estrutura:**
```
backend/tests/
├── test_auth_service.py          # ✅ Existe
├── test_portfolio_service.py      # ✅ Existe
├── test_rentabilidade_service.py  # ✅ Existe
├── test_irpf_service.py           # ❌ NOVO
├── test_treasury_service.py       # ❌ NOVO
├── test_goals_service.py          # ❌ NOVO
├── test_fixed_income_service.py   # ❌ NOVO
├── test_admin_router.py           # ❌ NOVO
├── test_integration_flows.py      # ❌ NOVO (end-to-end)
└── conftest.py                    # ✅ Existe
```

**Meta:** Cobertura mínima 50% → 70%

---

#### 3.2 🟡 Testes E2E (12-15h)
**Status:** ❌ NÃO INICIADO (0%)

**Setup Cypress:**
```bash
npm install -D cypress @cypress/webpack-dev-server
npx cypress open

# Criar testes em cypress/e2e/:
# - auth.cy.ts (login/register/logout)
# - portfolio.cy.ts (criar carteira, lançar transação)
# - rentabilidade.cy.ts (ver gráficos e KPIs)
# - proventos.cy.ts (dividendos)
```

---

#### 3.3 🟡 Layout Mobile Responsivo (6-8h)
**Status:** ⚠️ PARCIAL (BottomNav existe, mas páginas quebram)

**Testar/Corrigir em:**
- PatrimonioPage (gráficos overflow)
- RentabilidadePage (tabelas não scrollam)
- Modais em telas pequenas
- Sidebar responsivo

**Usar DevTools:** `Ctrl+Shift+K` → mobile view, testar em iPhone 12/Pixel 5

---

#### 3.4 🟢 Documentação de Arquitetura (6-8h)
**Status:** ❌ NÃO INICIADO

**Criar em `docs/`:**
- `ARCHITECTURE.md` — decisões de design, padrões
- `DATABASE_SCHEMA.md` — ERD comentado
- `DEPLOYMENT.md` — guia de deploy em produção
- `TROUBLESHOOTING.md` — problemas comuns
- `API_DESIGN.md` — padrões (paginação, filtros, erros)

---

#### 3.5 🟡 Completar AnalisePage & MetasPage (10-12h)
**Status:** ❌ STUBS VAZIOS

**AnalisePage:**
- Score de diversificação por setor
- Concentração por ativo com alertas
- Comparação vs. metas de alocação
- Sugestões de rebalanceamento

**MetasPage:**
- CRUD de metas
- Progresso visual
- Alertas de atingida/ultrapassada

---

### Checklist Sprint 3

- [ ] 3.1 — Cobertura de testes backend 70%+
- [ ] 3.2 — 10+ testes E2E passando
- [ ] 3.3 — App responsivo em mobile (iPhone 12 + Pixel 5)
- [ ] 3.4 — Documentação completa e atualizada
- [ ] 3.5 — AnalisePage e MetasPage funcionais

**Saída esperada:** Aplicativo pronto para produção com QA profissional

---

## 📈 Timeline Recomendada

```
Semana 1-2:  Sprint 1 (Performance + Produção)      30-40h
Semana 3-4:  Sprint 2 (Features Críticas)            40-60h
Semana 5-7:  Sprint 3 (Qualidade + UX)              40-50h
─────────────────────────────────────────────────────────
TOTAL:       ~120-150 horas  (8-12 semanas com 1 dev)
             (4-6 semanas com 2 devs)
```

---

## 🚀 Como Executar

### Daily Standup
```
1. O que foi feito ontem?
2. O que vai fazer hoje?
3. Tem bloqueadores?
→ Max 10 min
```

### PR Checklist (Antes de Merge)
```
- [ ] Feature implementada 100%
- [ ] Testes adicionados/atualizados
- [ ] Linting passa (npm run lint / flake8)
- [ ] TypeCheck passa (tsc / mypy)
- [ ] Sem console.log ou print statements
- [ ] Documentação atualizada
- [ ] Testado em staging
```

### Deploy Pipeline
```
1. Feature branch completa
2. PR aberta, código revisado
3. CI/CD passa (lint + test + build)
4. Merge para main
5. Deploy automático para staging
6. QA aprova
7. Deploy para produção
```

---

## 📚 Referências

| Documento | Uso |
|-----------|-----|
| `GAPS_ANALISE_COMPLETA.md` | Detalhes de cada gap |
| `ROADMAP_SPRINTS.md` | Roadmap original com status |
| `CHANGELOG.md` | Histórico de implementações |
| `QUERY_OPTIMIZATION.md` | Análise de performance |
| `.github/workflows/ci.yml` | Pipeline CI/CD |

---

## ✅ Success Criteria

Ao final de 8-12 semanas:

- ✅ Sprint 1: App pronto para produção
- ✅ Sprint 2: Todas as features planejadas implementadas
- ✅ Sprint 3: Cobertura de testes 70%+, UX mobile funcional
- ✅ Zero "multiple head revisions" ou erros de migration
- ✅ Performance baseline: queries < 200ms, cache hit > 50%
- ✅ 0 gaps críticos restantes, documentação completa

---

## 🎯 Próximos Passos (Hoje)

1. ✅ Escolher dev para coordenar Sprint 1
2. ✅ Criar issues no GitHub para cada tarefa
3. ✅ Configurar labels: `gap-1.1`, `gap-2.1`, etc
4. ✅ Primeira reunião de planejamento (30 min)
5. ✅ Começar com tarefa 1.1 (Índices PostgreSQL)

---

*Plano criado em 02/07/2026 — Abacus AI Agent*
