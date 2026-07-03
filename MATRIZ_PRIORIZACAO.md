# MATRIZ DE PRIORIZAÇÃO — Gaps SGI v2

**Gerada em:** 02 de Julho de 2026

---

## 🎯 Matriz Impacto vs Esforço

```
IMPACTO ALTO                                           
    ▲
    │
    │   🔴 CRÍTICOS (Fazer Primeiro)      🔴 RÁPIDO GANHO
    │   • CSV Import (2.1)  [12-15h]       • Índices (1.1) [2h]
    │   • Backup/Restore (2.2) [12-15h]   • Cache (1.3) [2-3h]
    │   • Testes Backend (3.1) [15-20h]    • Monit. (1.2) [1h]
    │
    │   🟡 IMPORTANTES               🟢 BAIXO IMPACTO
    │   • IRPF (2.3) [10-12h]       • Dark Mode [4-6h]
    │   • Audit Logs (2.4) [8-10h]  • Docs [6-8h]
    │   • Asset Drawer (2.5) [8-10h]• API Docs [2-3h]
    │
    │   🟡 MELHORIAS                 🟢 NICE-TO-HAVE
    │   • Mobile (3.3) [6-8h]       • Sprint 6A [2h]
    │   • AnalisePage (3.5) [10-12h]
    │   • MetasPage (3.5) [10-12h]
    │   • E2E Tests (3.2) [12-15h]
    │
    └─────────────────────────────────────────────────────► ESFORÇO BAIXO
    ESFORÇO ALTO                                    
```

---

## 🔥 Top 10 Prioridades (Ordem de Execução)

| # | Gap | Sprint | Criticidade | Impacto | Esforço | Ordem |
|---|-----|--------|-------------|---------|---------|-------|
| 1 | 1.1 Índices PostgreSQL | 1 | 🔴 CRÍTICO | Alto | 2h | **1º** |
| 2 | 1.2 Monitoramento Queries | 1 | 🔴 CRÍTICO | Alto | 1h | **2º** |
| 3 | 1.3 Cache Redis | 1 | 🔴 CRÍTICO | Alto | 2-3h | **3º** |
| 4 | 2.1 CSV Import | 2 | 🔴 CRÍTICO | Muito Alto | 12-15h | **4º** |
| 5 | 2.2 Backup/Restore | 2 | 🔴 CRÍTICO | Muito Alto | 12-15h | **5º** |
| 6 | 3.1 Testes Backend | 3 | 🟡 MÉDIO | Alto | 15-20h | **6º** |
| 7 | 2.3 IRPF Completo | 2 | 🟡 MÉDIO | Alto | 10-12h | **7º** |
| 8 | 3.2 Testes E2E | 3 | 🟡 MÉDIO | Alto | 12-15h | **8º** |
| 9 | 2.4 Audit Logs | 2 | 🟡 MÉDIO | Médio | 8-10h | **9º** |
| 10 | 1.4 Sprint 6A Compliance | 1 | 🟢 BAIXO | Médio | 2h | **10º** |

---

## 📅 Calendário de Execução

### SEMANA 1-2: Sprint 1 (Performance)

| Dia | Tarefa | Responsável | Status |
|-----|--------|-------------|--------|
| Seg-Ter | 1.1 Índices PostgreSQL | Backend | ⏳ |
| Ter-Qua | 1.2 Monitoramento | DevOps | ⏳ |
| Qua-Qui | 1.3 Cache Redis | Backend | ⏳ |
| Qui-Sex | 1.4 Sprint 6A Compliance | Qualquer um | ⏳ |
| Sex | 1.5 Setup Testes Frontend | Frontend | ⏳ |
| Sex | 1.6 Verify N+1 Fixes | Backend | ⏳ |
| Seg (Sem 2) | Teste Integração Sprint 1 | QA | ⏳ |

**Status Sprint 1:** Não iniciado

---

### SEMANA 3-4: Sprint 2 (Features)

| Semana | Tarefa | Responsável | Duração |
|--------|--------|-------------|---------|
| Sem 3 | 2.1 CSV Import Backend | Backend | 8h |
| Sem 3 | 2.1 CSV Import Frontend | Frontend | 4-7h |
| Sem 4 | 2.2 Backup/Restore | Backend + DevOps | 12-15h |
| Sem 3-4 | 2.3 IRPF + Export | Backend | 10-12h |
| Sem 4 | 2.4 Audit Logs | Backend | 8-10h |
| Sem 4 | 2.5 Asset Drawer | Frontend | 8-10h |

**Status Sprint 2:** Não iniciado

---

### SEMANA 5-7: Sprint 3 (Qualidade)

| Semana | Tarefa | Responsável | Meta |
|--------|--------|-------------|------|
| Sem 5 | 3.1 Backend Tests (batch 1) | Backend | +20 testes |
| Sem 5-6 | 3.1 Backend Tests (batch 2) | Backend | +20 testes |
| Sem 6 | 3.2 E2E Tests Setup + escrita | Frontend | 10+ testes |
| Sem 6 | 3.3 Mobile Responsivo | Frontend | 5+ breakpoints |
| Sem 7 | 3.4 Documentação | Qualquer um | 4 docs |
| Sem 7 | 3.5 AnalisePage + MetasPage | Frontend | 2 páginas |

**Status Sprint 3:** Não iniciado

---

## 💰 ROI (Return on Investment)

### Impacto por Sprint

**Sprint 1 (30-40h):** Ganho imediato de performance
- -30-50% latência em queries críticas
- Dashboard < 500ms (vs. 1-2s atualmente)
- Escalabilidade até 10M linhas em transactions

**Sprint 2 (40-60h):** Feature-complete
- Usuários conseguem importar ativos em massa
- Disaster recovery habilitado
- IRPF pronto para produção

**Sprint 3 (40-50h):** Profissionalização
- Confiança em código com testes
- UX mobile = desktop quality
- Documentação completa

### ROI Total

```
Tempo investido:     120-150 horas
Qualidade ganha:     0% → 90% (testes, performance, features)
Time velocity:       +40% (com documentação)
Bug reduction:       -60% (com testes)
User satisfaction:   +50% (performance + features + mobile)
```

---

## 🎯 Definição de Sucesso por Sprint

### Sprint 1 ✅ SUCESSO
- Latência queries críticas < 200ms (vs. 500-2000ms agora)
- Cache Redis hitrate > 50%
- 0 erros "Seq Scan" em EXPLAIN ANALYZE
- 5+ testes frontend passando
- 0 referências a APIs externas em docs públicas
- App não quebra em startup

### Sprint 2 ✅ SUCESSO
- CSV import funcional com validação completa
- Backup/restore testado e funcionando
- IRPF exporta PDF com cálculos corretos
- Audit logs registrando todas as ações
- Asset drawer abre ao clicar em ativos

### Sprint 3 ✅ SUCESSO
- Cobertura backend 70%+
- 10+ testes E2E passando
- App responsivo em iPhone 12 e Pixel 5
- Documentação completa (4 arquivos)
- AnalisePage e MetasPage funcionais

---

## 🚨 Riscos & Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|--------|-----------|
| Índices quebram queries | 🟢 Baixa | Alto | Criar em staging primeiro, EXPLAIN antes |
| CSV import corrompe dados | 🟡 Média | Alto | Transação atômica + testes + rollback |
| Testes tomam 2x do tempo | 🟡 Média | Médio | Pair programming, copy-paste de patterns |
| Backup falha em produção | 🟢 Baixa | Muito Alto | Testar 3x antes de deploy |
| Mobile breaks desktop | 🟢 Baixa | Médio | Mobile-first development |

---

## 📊 Rastreamento de Progresso

### Template Weekly Status

```markdown
## Semana [N] — [Intervalo datas]

### Sprint [X] — [Nome]

#### Completado
- [x] Tarefa 1 (2h)
- [x] Tarefa 2 (1.5h)
- [x] Tarefa 3 (4h)
**Total:** 7.5h / 40h estimado (19%)

#### Em Progresso
- [ ] Tarefa 4 — 60% completo, teste de integração pendente
- [ ] Tarefa 5 — início previsto amanhã

#### Bloqueadores
- ❌ Nenhum no momento
- ⚠️ Performance query X ainda > 300ms (vs. alvo 200ms)

#### Próxima Semana
- Finalizar Tarefa 4-5
- Iniciar Tarefa 6
- Code review completo

#### Métricas
- Velocity: 7.5h (meta: 40h/semana)
- Bugs encontrados em testes: 3 (0 críticos)
- Coverage: 45% → 48%
```

---

## 🔄 Process

### Daily (5 min)
```
1. O que foi feito ontem?
2. O que vai fazer hoje?
3. Tem bloqueador?
→ Slack ou standup presencial
```

### Weekly (30 min)
```
1. Review do progresso da semana
2. Testes de features completadas
3. Planejamento da próxima semana
4. Ajustes de timeline se necessário
```

### Bi-Weekly (1h)
```
1. Demo de features para stakeholders
2. Retrospectiva (o que foi bem, o que melhorar)
3. Discussão de arquitetura/padrões
4. Planejamento detalhado das 2 próximas semanas
```

---

## 🎬 Como Começar Hoje

### Checklist para o Dev Lead

- [ ] Ler `GAPS_ANALISE_COMPLETA.md` (20 min)
- [ ] Ler `PLANO_ACAO_EXECUTAVEL.md` (20 min)
- [ ] Ler `MATRIZ_PRIORIZACAO.md` (este arquivo) (10 min)
- [ ] Criar 6 issues no GitHub com labels `gap-1.1` até `gap-1.6`
- [ ] Estimar timing com time
- [ ] Agendar kick-off meeting (1h)
- [ ] Começar Sprint 1, Tarefa 1.1 amanhã

### Kick-off Meeting (1h)

```
15 min — Visão geral (ler slides do plano)
20 min — Q&A (dúvidas?)
15 min — Atribuição de tarefas Sprint 1
10 min — Próximos passos
```

---

*Matriz criada em 02/07/2026 — Abacus AI Agent*
