# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Concluído — Pipeline completo de mercado e proventos para renda variável nacional (04/07/2026) — #92 / PR #93

> Entrega consolida a coleta, normalização e materialização de proventos para ações, FIIs, ETFs nacionais e BDRs.

**Backend**
- Expansão de `asset_dividends` para Data Com, Data Ex, pagamento, aprovação, valor unitário, total, fatores, ISIN, payload bruto e eventos não-cash.
- Parser/backfill para eventos de renda variável nacional, cobrindo dividendos, JCP, rendimentos, amortização, bonificação e subscrição.
- Materialização de proventos por carteira com base na posição elegível na Data Com.
- Pipeline único por ativo para cadastro, preços, logo, eventos corporativos/proventos e materialização.
- Onboarding, seed e rotinas batch delegados ao pipeline único.
- CLIs operacionais para sincronização individual, pipeline individual e pipeline batch.
- Batch incremental diário para ativos mantidos em carteira.
- Ajustes de rate limit/fallback para evitar chamadas desnecessárias a fontes secundárias em ativos nacionais conhecidos.

**Frontend**
- Tabela de Proventos atualizada para separar Data Com e Data Ex.
- Base preparada para exibir status, tipo, quantidade elegível, valor unitário, valor total e total líquido.

**Validação**
- Pipeline validado manualmente para ação e FII.
- Batch completo para ativos mantidos em carteira: 18/18 OK.
- Batch incremental para ativos mantidos em carteira: 18/18 OK.
- Testes automatizados: `tests/test_market_pipeline_batch_service.py` e `tests/test_dividend_backfill_service.py` com 32 testes passando.

---

### Planejado — Continuidade após Proventos (Sprint corrente)

**Resumo**
- Corrigir dropdown de tabelas para não ficar preso/oculto dentro da área da tabela quando há poucos ativos.
- Revisar diferença conceitual entre variação do ativo/classe e rentabilidade total da classe.
- Alinhar KPIs da página Resumo para refletirem apenas valores atuais e sinais corretos, inclusive retorno negativo.

**Proventos**
- Validar a tela ponta a ponta com os dados materializados pelo novo pipeline.
- Revisar filtros, status e agregações com a nova base `asset_dividends`.

**Revisão visual e responsividade — #103**
- Planejar revisão geral da interface para reduzir densidade visual e melhorar espaçamentos.
- Padronizar cards, filtros, botões, tabelas, inputs, badges e estados.
- Revisar responsividade das páginas principais em desktop, tablet e mobile.
- Documentar plano em `docs/REVISAO_INTERFACE.md`.

**Patrimônio**
- Continuar refinamento visual em cards conforme issue #90.

---

### Planejado — Remoção de Menções a APIs Externas (Sprint 6A)

> Criticidade: **Alta** | Esforço: Baixo | Impacto: Segurança / Compliance

**Documentação pública (README, CHANGELOG, ROADMAP)**
- Substituir todos os nomes explícitos de APIs externas por termos genéricos.
- Exemplo: "provedor de cotações", "fonte de dados internacionais".
- Manter nomes técnicos apenas em `.env.example` com comentários descritivos.

**`backend/app/` (Swagger/OpenAPI)**
- Remover nomes de provedores em descrições de endpoints e schemas.

---

### Planejado — Otimização de Queries (Sprint 5B — pendente)

> Criticidade: **Alta** | Esforço: Alto | Impacto: Performance geral

**`backend/app/`**
- Mapear todas as queries críticas com `EXPLAIN ANALYZE`.
- Adicionar índices faltantes em colunas de filtro frequente.
- Corrigir padrões N+1 em listagens de posições e transações.
- Revisar joins em `rentabilidade_service`, `portfolio_class_evolution_service` e materialização de proventos.
- Documentar queries e tempos de execução antes e depois das otimizações.

---

### Planejado — Import de Ativos via CSV (Sprint 6D)

> Criticidade: **Alta** | Esforço: Médio | Impacto: UX / Onboarding

**Backend**
- `GET /api/v1/assets/csv-template` — retorna CSV modelo para download pelo usuário.
- `POST /api/v1/portfolios/{id}/import-csv` — valida e importa ativos em lote.
- Validação linha a linha com relatório de erros detalhado.
- Importação atômica (tudo ou rollback).

**Frontend**
- Botão "Importar via CSV" na tela de transações.
- Modal com preview das linhas + confirmação antes de importar.
- Download do modelo CSV diretamente no modal.

---

### Planejado — Logs de Auditoria por Usuário (Sprint 7B)

> Criticidade: Média | Esforço: Médio | Impacto: Governança interna

**Backend**
- Modelo `AuditLog` (user_id, action, resource, timestamp, metadata JSON).
- Middleware para captura automática de operações de escrita.
- Endpoint `GET /admin/users/{id}/audit` para superadmin com filtros.
- Exportação de log em CSV.

**Frontend**
- Tela de auditoria no painel superadmin.

---

### Planejado — Backup e Restore do Banco via Sistema (Sprint 10B)

> Criticidade: **Alta** | Esforço: Médio-Alto | Impacto: Resiliência / Disaster Recovery

**Backend**
- `POST /api/v1/admin/database/backup` — gera dump PostgreSQL e retorna arquivo para download.
- `POST /api/v1/admin/database/restore` — recebe arquivo de backup e restaura com confirmação por senha.
- Backup armazenado em volume Docker com TTL de 24h.
- Todas as operações registradas no `AuditLog`.
- Testes de integração: ciclo backup → restore → verificação de integridade.

**Frontend**
- Painel de administração com botões de backup e restore.
- Modal de confirmação com aviso de impacto antes do restore.

---

### Corrigido — Sprint 6B: bugs de boot + crash frontend + PatrimonioPage analítica (30/06/2026)

> Dois bugs críticos diagnosticados e corrigidos + reformulação completa da página Patrimônio.

**Bug 1 — Backend: `payment_date` ausente no banco**
- Migration 022 criada: adiciona colunas `payment_date`, `ex_date`, `value_per_unit`, `total_received` e `dividend_type` à tabela `dividends`.
- Resolve `_proventos_total` no `rentabilidade_service`: filtro `since` por `payment_date` agora funciona corretamente.

**Bug 2 — Frontend: crash `Cannot read properties of undefined (reading 'toFixed')`**
- Guards defensivos aplicados em formatações e props numéricas da `PatrimonioPage`.
- `formatPercent` e `formatBRL` protegidos contra `undefined`.

**Bug 3 — Backend: `ImportError` no boot**
- Funções `get_rentabilidade_por_ativo` e `get_rentabilidade_por_classe` adicionadas ao service.

**Sprint 6B — Reformulação da `PatrimonioPage`**
- Aba Histórico removida.
- Visão Geral com KPIs, evolução mensal, donut, Distribuição Ideal vs. Atual e tabela de posições.
- Aba Análise com Score HHI, Top 5 posições, concentração por classe e desvio do alvo.
- Treemap SVG puro com algoritmo Squarified.
- Toggle diário/mensal e seletor de período no gráfico de evolução.

---

### Concluído — Sprint 6C: limpeza de rotas e arquivos legados (30/06/2026)

- `HistoricoPage.tsx` removido e rota `/carteira/historico` removida.
- `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos.
- `Landing.tsx` restaurado com rota pública `/`.
- `App.tsx` mantido como legado sem re-export que quebrava o build.

---