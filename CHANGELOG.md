# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

---

## [Unreleased] — branch `stable-15jun`

### Concluído — Contratos críticos de autenticação e atualização de dependências (07/07/2026)

> Pacote validado localmente antes da PR `stable-15jun` → `main`, com foco em corrigir fluxos quebrados visíveis e reduzir pendências do Dependabot.

**Backend**
- Endpoint `POST /auth/forgot-password` exposto no router de autenticação.
- Endpoint `POST /auth/reset-password` exposto no router de autenticação.
- Schemas dedicados para solicitação e confirmação de recuperação de senha.
- Endpoint `PATCH /users/me/password` criado para alteração autenticada de senha.
- Validação da senha atual antes da troca de senha do usuário autenticado.
- Atualizações de dependências backend aplicadas em blocos pequenos: `email-validator`, `yfinance`, `fastapi` e `uvicorn`.

**Frontend**
- Fluxo “Esqueci senha” corrigido para usar o client Axios já prefixado com `/api/v1`, evitando chamadas duplicadas para `/api/v1/api/v1/...`.
- Tela de recuperação de senha validada localmente após a correção dos endpoints.
- Tela de Configurações validada para alteração de senha com o novo contrato backend.
- Build Vite corrigido removendo `--configLoader native`, que quebrava o Docker ao carregar `vite.config.ts`.
- `jsdom` atualizado e validado com Vitest.

**CI/CD**
- GitHub Actions centrais atualizadas: `actions/checkout`, `actions/setup-python` e `actions/setup-node`.
- PRs redundantes do Dependabot fechados após aplicação direta e validação em `stable-15jun`.

**Validação local reportada**
- `docker compose up -d --build backend frontend` subiu backend, frontend, banco e Redis sem erros.
- Login validado com sucesso.
- Fluxo “Esqueci senha” validado com sucesso.
- Alteração de senha em Configurações validada com sucesso.
- `npm test` executado com Vitest e teste de `KpiCard` passando.

---

### Concluído — Validação da página Proventos após pipeline completo (06/07/2026) — #95

> Continuidade da entrega #92 / PR #93, validando a experiência da página Proventos com dados materializados pelo pipeline de renda variável nacional.

**Backend**
- Agregações de proventos revisadas para considerar elegibilidade por Data Com, com Data Ex como fallback.
- Eventos não-cash, como bonificação e subscrição, mantidos fora dos totais financeiros.
- `summary` de proventos passou a aceitar os mesmos filtros consumidos pela listagem: status, ano, classe de ativo e tipo de evento.
- Histórico mensal e distribuição preservam apenas eventos financeiros nos totais.

**Frontend**
- KPIs da página Proventos conectados aos mesmos filtros da tabela.
- Tabela de Proventos revisada para simplificar leitura e remover a coluna técnica “Natureza”.
- Cards mobile alinhados à mesma simplificação da tabela desktop.
- Ajustes pontuais em Transações para garantir botões de edição e exclusão visíveis na tabela.

**Testes**
- Cobertura adicionada em `backend/tests/test_proventos_issue95.py`.
- Cenários cobertos: cash vs. não-cash, elegibilidade por Data Com e agregações sem inflar totais com eventos não financeiros.

---

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

**Contratos frontend/backend**
- Corrigir importação CSV autenticada, `dry_run=false` e template CSV (#82).
- Implementar download de backup e endurecer restore com confirmação forte, lock e auditoria (#83).

**Admin**
- Corrigir edição de usuários e alteração de perfil pelo superadmin (#98).

**Compliance de documentação/API**
- Substituir nomes explícitos de provedores externos por termos genéricos na documentação pública, Swagger/OpenAPI e mensagens públicas (#80).

**Auth**
- Implementar login com Google OAuth (#97).

**Performance**
- Mapear queries críticas com `EXPLAIN ANALYZE`.
- Adicionar índices faltantes.
- Corrigir padrões N+1 em listagens de posições e transações.

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
