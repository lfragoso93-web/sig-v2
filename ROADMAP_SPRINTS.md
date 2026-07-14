# Roadmap de Sprints — SGI v2

> Última atualização: 14/07/2026

Este documento preserva o histórico de sprints. O acompanhamento modular atual está em [`ROADMAP.md`](./ROADMAP.md).

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

### Sprint 5L — Arquitetura DB-first e TWR

- [x] Remover consultas externas do motor de snapshots.
- [x] Criar auditoria de cobertura por ativo.
- [x] Sincronizar lacunas de preços de forma idempotente.
- [x] Adicionar metadados persistentes de provedor nos ativos.
- [x] Criar smart sync com `HISTORY_START_EXHAUSTED`.
- [x] Criar `full_market_rebuild` como comando operacional oficial.
- [x] Migrar endpoints de evolução diária e mensal para leitura enriquecida.
- [x] Calcular KPIs de rentabilidade por TWR.
- [x] Materializar proventos em lotes seguros.
- [x] Sanitizar preços inválidos antes da persistência.
- [x] Usar histórico máximo quando a fonte suportar.
- [x] Separar Tesouro Direto do pipeline genérico de preços.

---

## 🔄 Em desenvolvimento

### Rentabilidade

- [x] Backend TWR para Hoje, Mês, 12 meses e Desde o início.
- [ ] Ajustar cards visuais.
- [ ] Exibir indicadores de qualidade (`has_partial_prices`, `return_is_estimated`).

### Resumo

- [ ] Revalidar cards contra a camada canônica.
- [ ] Confirmar Resultado incluindo proventos materializados.
- [ ] Revisar divergências entre cards do Resumo e Patrimônio.
- [ ] Corrigir overflow de dropdowns quando necessário.

### Tesouro Direto

- [x] Catálogo e preços atuais dedicados.
- [x] Histórico dedicado persistido.
- [ ] Garantir consumo dedicado no snapshot.

### Provedores e cobertura

- [x] Gap sync e smart sync.
- [x] Histórico máximo por capacidade.
- [ ] Provider router definitivo.
- [ ] Roteamento definitivo de cripto.
- [ ] Evitar duplicação de histórico para mercado fracionário.

### Motor de Eventos Corporativos — Issue #129

#### Fundação concluída

- [x] Adicionar tipo `TICKER_CHANGE`.
- [x] Registrar alias histórico e evento idempotente por carteira.
- [x] Calcular saldo remanescente na data efetiva.
- [x] Preservar quantidade, custo total e preço médio.
- [x] Manter compras e vendas históricas intactas.
- [x] Aplicar conversão automática simples 1:1.

#### Próximos blocos

- [ ] Executar spike técnico com fonte complementar.
- [ ] Mapear splits, grupamentos e cobertura por classe.
- [ ] Implementar providers de eventos corporativos.
- [ ] Adicionar simulação, confirmação e rollback.
- [ ] Cobrir bonificações, incorporações, fusões e conversões complexas.
- [ ] Criar administração e auditoria operacional dos eventos.

---

## 🔄 Próximas entregas prioritárias

1. Finalizar o consumo dedicado de Tesouro nos snapshots.
2. Resolver referência canônica de preços para mercado fracionário.
3. Ajustar UI da página Rentabilidade.
4. Revisar cards da página Resumo.
5. Validar novamente o `full_market_rebuild`.
6. Abrir PR única `stable-15jun` → `main` após validação.

---

## 📋 Backlog planejado

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

### IRPF — Issue #56

- [ ] Cálculo por ano-calendário.
- [ ] Isenção de vendas mensais.
- [ ] Day trade e swing trade.
- [ ] Relatórios e exportações.
- [ ] Testes de ganho de capital.

### Análise de Carteira — Issue #57

- [ ] Diversificação por setor e classe.
- [ ] Alertas de concentração.
- [ ] Comparação com metas.
- [ ] Sugestões de rebalanceamento.

### Janela Global do Ativo — Issue #58

- [ ] Drawer global do ativo.
- [ ] Histórico de preços.
- [ ] Histórico de proventos.
- [ ] Posição, custo médio e resultado.

### Provedores configuráveis — Issue #127

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
