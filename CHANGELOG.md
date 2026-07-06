# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

---

## [Unreleased] — branch `stable-15jun`

### Concluído — Revisão visual e responsividade do sistema (06/07/2026) — #103 / PRs #104–#108

> Sequência de ajustes visuais que consolidou um novo baseline de interface para o SGI v2.

**Base visual**
- Definido padrão de cards com mais respiro interno, largura controlada e menor densidade visual.
- Padronizados KPIs, headers de seção, filtros, tabelas e cards com comportamento mais consistente.
- Ajustado comportamento responsivo para desktop, tablet, mobile e telas ultrawide.
- Telas de entrada — Login, Registro e Recuperar Senha — definidas como referência visual para o restante do sistema.

**Páginas revisadas**
- Resumo: KPIs, variação, dropdown de ativos e responsividade das tabelas.
- Proventos: cards, filtros, tabelas, paginação e layout fluido.
- Patrimônio: simplificação da consolidação e remoção de posições redundantes.
- Rentabilidade: organização de blocos por classe e por ativo.
- Transações: busca, densidade dos cards e comportamento em telas menores.
- Configurações: abas, formulários, cards e lista de carteiras.

**Estado do projeto**
- Revisão visual geral pausada em um ponto estável.
- Próxima retomada deve preservar o padrão visual consolidado nesta fase.

---

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

### Próximos focos sugeridos

**Auth**
- Implementar login com Google OAuth (#97).

**Admin**
- Corrigir edição de usuários e alteração de perfil pelo superadmin (#98).

**Compliance de documentação/API**
- Substituir nomes explícitos de provedores externos por termos genéricos na documentação pública, Swagger/OpenAPI e mensagens públicas.

**Performance**
- Mapear queries críticas com `EXPLAIN ANALYZE`.
- Adicionar índices faltantes.
- Corrigir padrões N+1 em listagens de posições e transações.

**Importação CSV**
- Preparar fluxo de importação de ativos em lote com validação e preview.

---

### Planejado — Remoção de Menções a APIs Externas

> Criticidade: Alta | Esforço: Baixo | Impacto: Segurança / Compliance

- Substituir todos os nomes explícitos de APIs externas por termos genéricos.
- Manter nomes técnicos apenas em `.env.example` com comentários descritivos.
- Remover nomes de provedores em descrições de endpoints e schemas.

---

### Planejado — Otimização de Queries

> Criticidade: Alta | Esforço: Alto | Impacto: Performance geral

- Mapear todas as queries críticas com `EXPLAIN ANALYZE`.
- Adicionar índices faltantes em colunas de filtro frequente.
- Corrigir padrões N+1 em listagens de posições e transações.
- Revisar joins em serviços de rentabilidade, evolução por classe e materialização de proventos.

---

### Planejado — Import de Ativos via CSV

> Criticidade: Alta | Esforço: Médio | Impacto: UX / Onboarding

- Endpoint para baixar CSV modelo.
- Endpoint para validar e importar ativos em lote.
- Validação linha a linha com relatório de erros detalhado.
- Importação atômica.
- Modal com preview das linhas antes de importar.

---

### Planejado — Logs de Auditoria por Usuário

> Criticidade: Média | Esforço: Médio | Impacto: Governança interna

- Modelo `AuditLog`.
- Captura automática de operações de escrita.
- Endpoint para superadmin consultar auditoria por usuário.
- Exportação de log em CSV.

---

### Planejado — Backup e Restore do Banco via Sistema

> Criticidade: Alta | Esforço: Médio-Alto | Impacto: Resiliência / Disaster Recovery

- Endpoint de backup do banco para superadmin.
- Endpoint de restore com confirmação por senha.
- Backup temporário em volume Docker.
- Registro das operações em auditoria.
- Teste de integração backup → restore → verificação de integridade.

---

### Corrigido — Sprint 6B: bugs de boot + crash frontend + PatrimonioPage analítica (30/06/2026)

- Migration 022 criada para colunas de proventos na tabela `dividends`.
- Guards defensivos aplicados em formatações e props numéricas da `PatrimonioPage`.
- Funções de rentabilidade por ativo/classe adicionadas ao service.
- Aba Histórico removida da página Patrimônio.
- Visão Geral com KPIs, evolução mensal, donut, Distribuição Ideal vs. Atual e tabela de posições.
- Aba Análise com Score HHI, Top 5 posições, concentração por classe e desvio do alvo.
- Treemap SVG puro com algoritmo Squarified.

---

### Concluído — Sprint 6C: limpeza de rotas e arquivos legados (30/06/2026)

- `HistoricoPage.tsx` removido e rota `/carteira/historico` removida.
- `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos.
- `Landing.tsx` restaurado com rota pública `/`.
- `App.tsx` mantido como legado sem re-export que quebrava o build.

---
