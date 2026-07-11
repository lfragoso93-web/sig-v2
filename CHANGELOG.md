# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

---

## [Unreleased] — branch `stable-15jun`

### Em desenvolvimento — Compliance público e hardening documental (11/07/2026)

#### Documentação

- README, roadmap, changelog e documentos auxiliares passaram a usar termos genéricos para fontes externas de dados.
- Documentos antigos de análise foram atualizados para refletir o estado atual do sistema.
- Prioridades concluídas foram removidas das seções de próximos focos.

#### API pública

- OpenAPI passou a sanitizar descrições, exemplos e valores padrão que identifiquem fornecedores externos.
- Endpoints públicos de cotação passaram a devolver uma origem genérica de dados de mercado.
- Exceções exibidas em modo debug passaram a remover nomes de fornecedores antes da resposta HTTP.
- Logs internos e módulos de integração preservam os identificadores técnicos necessários à operação.

#### Testes

- Adicionado teste de compliance dos documentos públicos.
- Adicionado teste de compliance do OpenAPI e dos metadados públicos de cotação.

---

### Concluído — Resumo, administração e integridade operacional (11/07/2026)

> Entrega consolidada na PR #126 e validada antes do merge em `main`.

#### Backend

- Variação diária por classe separada da rentabilidade acumulada.
- Preços anteriores passaram a compor métricas diárias das posições agrupadas.
- Exclusão de carteira passou a remover explicitamente transações, posições, snapshots, metas, proventos, eventos corporativos, renda fixa e relatórios dependentes.
- Logs de auditoria são preservados com `portfolio_id` desacoplado antes da exclusão.
- Serviços administrativos de usuários completados com criação, listagem, edição, exclusão e contagem.
- Validações adicionadas para unicidade, permissões, autoedição e proteção do último superadmin.
- Schemas de usuários ampliados para atender o painel administrativo.
- Importação CSV ajustada para tratar corretamente registros já existentes e resultados de validação.

#### Frontend

- Menu de ações da tabela de posições passou a usar portal e posicionamento relativo à viewport.
- Dropdown deixa de ser cortado pelo contêiner da tabela, inclusive em carteiras com poucas posições.
- Cabeçalho das classes passou a exibir variação diária real, sem reutilizar a rentabilidade acumulada.
- Modal de importação CSV passou a bloquear a confirmação quando houver erros, linhas ignoradas ou falhas globais.
- Caches de Resumo, Patrimônio, Rentabilidade, metas e transações são invalidados após importação bem-sucedida.
- Painel administrativo modernizado e edição de papel/status integrada ao backend.
- Painel de backup simplificado para refletir apenas ações atualmente suportadas.
- Página Patrimônio ajustada aos contratos atualizados de posições.

#### Testes

- Cobertura backend ampliada para métricas de grupos, exclusão de carteiras, CSV e regras administrativas.
- Adicionado teste frontend para tabela de posições e comportamento do menu contextual.

---

### Concluído — Consolidação financeira, CSV, Proventos e Tesouro Direto (10/07/2026)

> Pacote validado localmente antes da PR `stable-15jun` → `main`.

#### Backend

- Criado serviço canônico de KPIs de carteira.
- Resumo, Patrimônio e Performance passaram a compartilhar os mesmos totais.
- Evolução patrimonial diária e mensal restaurada com fallback histórico.
- Manutenção automática de snapshots adicionada ao scheduler.
- Ganho realizado, retorno mensal e retorno de 12 meses corrigidos.
- Importação CSV conectada corretamente ao serviço transacional.
- Upload CSV com suporte a UTF-8 BOM, UTF-8 e Latin-1.
- `dry_run`, persistência e invalidação de caches financeiros cobertos.
- Mensagens conhecidas da importação traduzidas para português.
- Isolamento de carteiras por usuário corrigido, inclusive para superadmins.
- Seed histórico de proventos adicionado e integrado ao sync diário.
- Seed histórico tornado idempotente com `ON CONFLICT DO NOTHING`.
- Tickers sem histórico passaram a usar cooldown de indisponibilidade.
- Catálogo de Tesouro Direto consolidado com symbols canônicos.
- Adicionado fallback de preços por fonte oficial secundária para RendA+ e Educa+.

#### Frontend

- KPIs de Resumo, Patrimônio e Rentabilidade normalizados.
- Gráficos de evolução voltaram a carregar.
- Removido backfill manual da interface de Patrimônio.
- Cards de Rentabilidade tiveram rótulos e semântica corrigidos.
- Importação CSV validada com preview e resultado misto.
- Página Proventos passou a usar apenas a carteira selecionada no topbar.
- Página Rentabilidade passou a usar apenas a carteira selecionada no topbar.
- Estados vazios preservados quando nenhuma carteira está selecionada.

#### Testes e validação

- Testes de portfolio e performance aprovados.
- Testes de upload, dry-run, persistência e cache do CSV adicionados.
- Typecheck e build do frontend aprovados.
- Docker Compose validado com backend, frontend, PostgreSQL e Redis.
- Importação CSV validada funcionalmente.
- Sincronização de proventos reexecutada sem violações de unicidade.

---

### Concluído — Contratos críticos de autenticação e Dependabot (07/07/2026)

- Endpoints de recuperação e redefinição de senha expostos.
- Prefixo duplicado `/api/v1` corrigido no frontend.
- Endpoint autenticado de alteração de senha criado.
- Build Vite em Docker corrigido.
- Dependências backend, frontend e GitHub Actions atualizadas.

---

### Concluído — Validação da página Proventos pós-pipeline (06/07/2026) — #95

- Agregações revisadas por Data Com com fallback para Data Ex.
- Eventos não-cash excluídos dos totais financeiros.
- KPIs sincronizados com filtros da tabela.
- Testes de elegibilidade e agregação adicionados.

---

### Concluído — Revisão visual e responsividade (06/07/2026) — #103

- Cards, KPIs, filtros, tabelas e estados vazios padronizados.
- Responsividade revisada em desktop, tablet, mobile e ultrawide.
- Resumo, Patrimônio, Proventos, Transações, Rentabilidade e Configurações revisados.

---

### Concluído — Pipeline completo de mercado e proventos (04/07/2026) — #92 / PR #93

- Eventos corporativos expandidos.
- Materialização de proventos por carteira.
- Pipeline único por ativo.
- Batch incremental diário.
- Testes automatizados de parser, materialização e pipeline.

---

## Próximos focos

- Concluir compliance público e configuração compatível (#80).
- Robustecer Backup/Restore (#83).
- Implementar Google OAuth (#97).
- Refinar a experiência da página Patrimônio (#90).
- Avançar em IRPF (#56), Análise (#57) e Janela Global do Ativo (#58).
