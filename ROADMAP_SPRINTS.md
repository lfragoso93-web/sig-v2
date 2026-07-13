# Roadmap de Sprints — SGI v2

> Última atualização: 13/07/2026

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

### Sprint 5J — Estabilização funcional e contratos operacionais

- [x] KPIs canônicos para Resumo, Patrimônio e Rentabilidade.
- [x] Variação diária separada da rentabilidade acumulada.
- [x] Importação CSV autenticada, integral e com `dry_run`.
- [x] Administração de usuários e proteção do último superadmin.
- [x] Compliance de documentação pública e contratos expostos.
- [x] Proventos históricos, Tesouro Direto e integridade de carteiras.
- [x] Exclusão segura de carteiras com auditoria preservada.

### Sprint 5K — Integridade histórica e modernização de dados

- [x] Inventário da integração atual com dados de mercado.
- [x] Cliente isolado para API v2.
- [x] Resolução de tickers antigos em lotes.
- [x] Persistência de aliases históricos.
- [x] Validação temporal de renome pela data da operação.
- [x] Filtros interativos no modal de importação CSV.
- [x] Rebuild automático de snapshots após importação.
- [x] Edição de nome e descrição de carteiras.
- [x] Teste estrutural contra IDs Alembic duplicados.
- [x] Suporte do entrypoint a múltiplas heads Alembic válidas.

---

## 🔄 Em desenvolvimento

### Motor de Eventos Corporativos — Issue #129

#### Fundação concluída

- [x] Adicionar tipo `TICKER_CHANGE`.
- [x] Registrar alias histórico e evento idempotente por carteira.
- [x] Calcular saldo remanescente na data efetiva.
- [x] Preservar quantidade, custo total e preço médio.
- [x] Manter compras e vendas históricas intactas.
- [x] Aplicar conversão automática simples 1:1.

#### Próximos blocos

- [ ] Executar spike técnico com HG Brasil.
- [ ] Mapear splits, grupamentos e cobertura por classe.
- [ ] Implementar providers de eventos corporativos.
- [ ] Adicionar simulação, confirmação e rollback.
- [ ] Cobrir bonificações, incorporações, fusões e conversões complexas.
- [ ] Criar administração e auditoria operacional dos eventos.

### Evolução da integração de mercado v2 — Issue #130

#### Fundação concluída

- [x] Inventariar endpoints e consumidores atuais.
- [x] Criar cliente v2 e DTO interno de resolução.
- [x] Resolver tickers antigos antes da importação.
- [x] Tratar falhas de rede, HTTP e payload inválido sem interromper o CSV.
- [x] Integrar renomes ao motor de eventos corporativos.

#### Próximos blocos

- [ ] Integrar endpoint de cobertura por ticker.
- [ ] Persistir cobertura e data da última verificação.
- [ ] Migrar gradualmente cotações, histórico e proventos para DTOs internos.
- [ ] Separar bonificações e subscrições de proventos monetários.
- [ ] Enriquecer FIIs com indicadores, imóveis, vacância, carteira e relatórios.
- [ ] Enriquecer ações com fundamentos e demonstrações financeiras.
- [ ] Integrar câmbio histórico e macroeconomia como fonte complementar.

---

## 🔄 Próximas entregas prioritárias

### Backup/Restore — Issue #83

- [ ] Implementar geração autenticada de backup para download.
- [ ] Adicionar checksum, lock e auditoria da operação.
- [ ] Definir retenção e limpeza de arquivos temporários.
- [ ] Validar restore em ambiente isolado.
- [ ] Projetar restore controlado como fase posterior.

### Auth — Issue #97

- [ ] Implementar Google OAuth.
- [ ] Vincular conta social a usuário existente.
- [ ] Cobrir login, callback e erros.

### UX Patrimônio — Issue #90

- [ ] Reorganizar a página em cards claros e responsivos.
- [ ] Preservar os contratos financeiros canônicos.
- [ ] Separar composição, metas, concentração e posições.

### UX Proventos — Issue #131

- [ ] Exibir tooltip mensal com detalhamento por classe.
- [ ] Respeitar filtros ativos e conciliar o total mensal.
- [ ] Suportar hover, teclado e toque.
- [ ] Evitar cortes por overflow usando portal quando necessário.

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

### Backlog arquitetural — Provedores configuráveis — Issue #127

- [ ] Criar registry/factory de provedores por capacidade.
- [ ] Permitir configuração pelo Superadmin com credenciais criptografadas.
- [ ] Preservar fallback para `.env`.
- [ ] Adicionar health check, teste de conexão, auditoria e rollback.

---

## Processo de desenvolvimento

1. Desenvolvimento sempre na `stable-15jun`.
2. Commits pequenos e isolados.
3. Validação local de build, testes e fluxo funcional.
4. Atualização de README, roadmap e changelog ao consolidar uma entrega.
5. PR única para `main` ao concluir um bloco estável.