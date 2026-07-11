# Roadmap de Sprints — SGI v2

> Última atualização: 11/07/2026

---

## ✅ Sprints concluídas

### Sprint 1 — Fundação
- FastAPI, SQLAlchemy async, Alembic, PostgreSQL e Redis.
- Docker Compose, autenticação JWT e health checks.
- Módulos base de usuários, carteiras, transações e posições.

### Sprint 2 — Core Financeiro
- Proventos, performance, câmbio, Tesouro Direto e ativos internacionais.
- Cache Redis, scheduler e rate limiting.

### Sprint 3 — Funcionalidades avançadas base
- Goals, IRPF base, analysis base, renda fixa, cotações, preços e metas por classe.

### Sprint 4 — Catálogo e dados
- Seed idempotente de ativos.
- Backfill de preços.
- Onboarding e jobs incrementais.

### Sprint 5 — Dashboard e experiência principal
- Resumo, Patrimônio, Rentabilidade, Proventos e interface responsiva.
- Gráficos, benchmarks, distribuição por classe e metas.

### Sprint 5G/5H — Pipeline de mercado e proventos
- Eventos corporativos completos.
- Data Com, Data Ex e pagamento.
- Materialização por carteira.
- Validação de eventos cash e não-cash.

### Sprint 5I — Auth, dependências e CI
- Recuperação e alteração de senha.
- Correção do build Vite em Docker.
- Atualizações Dependabot e GitHub Actions.

### Sprint 6B/6C/6E — Patrimônio analítico e revisão visual
- Score HHI, Top 5 posições e desvio de metas.
- Limpeza de rotas legadas.
- Baseline visual e responsivo consolidado.

---

## ✅ Sprint 5J — Estabilização funcional e contratos operacionais

### 5J-A — Resumo e consolidação financeira — Issue #124

- [x] Unificar KPIs de Resumo, Patrimônio e Rentabilidade.
- [x] Criar serviço canônico de patrimônio e resultado.
- [x] Corrigir resultados negativos e semântica dos cards.
- [x] Restaurar evolução diária e mensal.
- [x] Automatizar manutenção de snapshots.
- [x] Corrigir ganho realizado, retorno mensal e retorno de 12 meses.
- [x] Remover seletores locais de carteira em Rentabilidade e Proventos.
- [x] Corrigir dropdown/lista suspensa cortada na tabela do Resumo.
- [x] Separar variação diária da rentabilidade acumulada por classe.
- [x] Adicionar teste frontend para a tabela de posições.
- [ ] Finalizar QA de carteira vazia, apenas renda fixa e posições zeradas.

### 5J-B — Importação CSV — Issue #82

- [x] Modelo CSV para download.
- [x] Preview antes da importação.
- [x] Upload autenticado.
- [x] `dry_run` e persistência efetiva.
- [x] Validação linha a linha.
- [x] Mensagens em português.
- [x] Bloquear confirmação enquanto houver erros, linhas ignoradas ou falhas globais.
- [x] Invalidação dos caches financeiros.
- [x] Testes de upload, dry-run e persistência.

### 5J-F — Proventos históricos e robustez

- [x] Página vinculada somente à carteira global do topbar.
- [x] Seed histórico completo por ativo.
- [x] BRAPI como fonte principal e complemento histórico.
- [x] Materialização por posição elegível.
- [x] UPSERT idempotente pela constraint de evento.
- [x] Tratamento de tickers indisponíveis e cooldown temporário.
- [x] Redução de ruído do coletor histórico.
- [ ] Adicionar testes específicos de reexecução e indisponibilidade.
- [ ] Revisar consistência entre total recebido e KPIs canônicos.

### 5J-G — Tesouro Direto

- [x] Catálogo canônico de títulos.
- [x] Normalização de RendA+ e Educa+.
- [x] Histórico e snapshots em `asset_prices`.
- [x] Fallback do Tesouro Transparente para títulos sem `indicators`.
- [ ] Validar localmente preços de todos os RendA+ mantidos em carteira.
- [ ] Adicionar testes do fallback de preço.

### 5J-H — Integridade de carteiras

- [x] Excluir dependências da carteira de forma explícita.
- [x] Preservar registros de auditoria desacoplando `portfolio_id` antes da exclusão.
- [x] Invalidar caches após alterações e exclusões.
- [ ] Executar QA com carteiras contendo todas as classes de ativos.

---

## 🔄 Próximas entregas prioritárias

### 5J-C — Backup/Restore — Issue #83

- [ ] Endpoint autenticado para download.
- [ ] Confirmação forte no restore.
- [ ] Lock global.
- [ ] Auditoria e status da operação.
- [ ] Storage persistente.
- [x] Simplificar a interface administrativa removendo ações ainda não suportadas.

### 5J-D — Administração de usuários — Issue #98

- [x] Implementar serviços de criação, listagem, edição e exclusão.
- [x] Corrigir edição de nome, papel e status do usuário.
- [x] Revisar permissões de superadmin.
- [x] Proteger o último superadmin.
- [x] Ajustar schemas usados pelo painel administrativo.
- [x] Migrar o painel para os tokens visuais atuais.
- [ ] Validar isolamento de dados entre contas em QA funcional.

### 5J-E — Compliance — Issue #80

- [ ] Remover nomes explícitos de provedores da documentação pública.
- [ ] Revisar Swagger/OpenAPI e mensagens públicas.
- [ ] Manter detalhes técnicos apenas em arquivos internos e configuração.

### Auth — Issue #97

- [ ] Implementar Google OAuth.
- [ ] Vincular conta social a usuário existente.
- [ ] Cobrir login, callback e erros.

---

## 📋 Sprints planejadas

### Sprint 7 — IRPF — Issue #56

- [ ] Cálculo por ano-calendário.
- [ ] Isenção de vendas mensais.
- [ ] Day trade e swing trade.
- [ ] Relatórios e exportações.
- [ ] Testes de ganho de capital.

### Sprint 8 — Análise de Carteira — Issue #57

- [ ] Diversificação por setor e classe.
- [ ] Alertas de concentração.
- [ ] Comparação com metas.
- [ ] Sugestões de rebalanceamento.

### Sprint 9 — Janela Global do Ativo — Issue #58

- [ ] Drawer global do ativo.
- [ ] Histórico de preços.
- [ ] Histórico de proventos.
- [ ] Posição, custo médio e resultado.

---

## Processo de desenvolvimento

1. Desenvolvimento sempre na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação local de build, testes e fluxo funcional.
4. Atualização de README, roadmap e changelog ao consolidar uma entrega.
5. PR única para `main` ao concluir um bloco estável.