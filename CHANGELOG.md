# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

---

## [Unreleased] — branch `stable-15jun`

### Adicionado — Arquitetura DB-first, histórico canônico e TWR (14/07/2026)

#### Backend

- Novo orquestrador operacional `full_market_rebuild` para manutenção completa de mercado.
- Auditoria de cobertura histórica por ativo.
- Sincronização idempotente de lacunas de preços.
- Locks por ativo no gap sync.
- Concorrência controlada no backfill global.
- Metadados persistentes de provedor nos ativos:
  - `provider`;
  - `provider_symbol`;
  - `provider_status`;
  - `provider_last_sync_at`;
  - `provider_last_error`;
  - `provider_attempts`.
- Smart sync com `HISTORY_START_EXHAUSTED` para evitar repetição de histórico inicial já esgotado.
- Uso de histórico máximo quando a fonte e rota suportam essa capacidade.
- Uso de `period=max` no fallback internacional de histórico amplo.
- Sanitização de preços antes da persistência em `asset_prices`.
- Resumo agregado de preços rejeitados por ativo/fonte.
- Normalização de símbolo de provedor para mercado fracionário.
- Tesouro Direto removido do pipeline genérico de gap sync.
- Serviço dedicado de histórico de Tesouro preservado como fonte da classe.
- Materialização de proventos em lotes seguros para evitar limite de parâmetros do driver.
- Propagação de erros internos dos serviços para o status final do rebuild.
- Snapshots TWR reconstruídos exclusivamente com dados persistidos no banco.
- Endpoints de evolução diária e mensal migrados para leitura enriquecida.
- KPIs de Rentabilidade passaram a expor retorno diário, mensal, 12 meses e desde o início.

#### Regras de negócio

- Snapshots não fazem chamadas externas.
- Resultado financeiro permanece separado de rentabilidade percentual.
- Resultado considera ganho realizado, ganho não realizado e proventos recebidos.
- Rentabilidade usa composição TWR diária.
- Classes sem cotação de mercado genérica não entram na sincronização de preços.
- Lacunas antigas sem histórico adicional são marcadas como esgotadas, não como erro recorrente.

#### Operação

- Comando oficial:

```bash
python -m app.cli.full_market_rebuild
```

- O rebuild executa:
  1. catálogo e preços;
  2. Tesouro Direto;
  3. benchmarks;
  4. proventos;
  5. snapshots TWR;
  6. auditoria final.
- O status final agora reflete erros internos retornados pelas etapas.
- Documentação operacional adicionada para execução via Docker e PowerShell.

#### Documentação

- README atualizado para a arquitetura DB-first.
- Adicionado `ROADMAP.md` modular.
- Atualizado `ROADMAP_SPRINTS.md` com a Sprint 5L.
- Adicionados documentos:
  - `docs/architecture.md`;
  - `docs/price-history.md`;
  - `docs/providers.md`;
  - `docs/operations.md`;
  - `docs/snapshots.md`;
  - `docs/canonical-data.md`;
  - `docs/rentabilidade.md`.

#### Pendências registradas

- Consumo dedicado de Tesouro nos snapshots.
- Referência canônica de preço para mercado fracionário sem duplicação física de histórico.
- Provider router definitivo.
- Roteamento final de cripto.
- Ajuste visual dos cards da página Rentabilidade.
- Revisão dos cards da página Resumo.

---

### Adicionado — Integração v2, aliases e eventos corporativos (13/07/2026)

#### Backend

- Cliente isolado para a API v2 do provedor principal de mercado.
- DTO interno para resolução de tickers.
- Resolução de tickers antigos em lotes de até 20 símbolos.
- Modelo e migration de aliases históricos de ativos.
- Novo tipo de evento corporativo `TICKER_CHANGE`.
- Registro idempotente de renomes por carteira, ticker antigo, ticker atual e data efetiva.
- Conversão automática de saldo remanescente para o ticker atual.
- Preservação de quantidade, custo total e preço médio durante a conversão.
- Reconstrução automática de snapshots diários após importação CSV.
- Invalidação de snapshots a partir da primeira transação e novo backfill em segundo plano.
- Teste estrutural para impedir IDs Alembic duplicados.
- Entry point atualizado para aplicar múltiplas heads Alembic válidas.

#### Frontend

- Cards de linhas válidas, avisos e erros do CSV passaram a funcionar como filtros.
- Clique novamente ou fora da área restaura a visualização completa.
- Modal de edição de carteira adicionado ao seletor global.
- Usuário pode alterar nome e descrição das próprias carteiras.
- Hook de atualização de carteira corrigido para usar `PATCH`.

#### Regras de negócio

- Ticker antigo é aceito quando a operação ocorreu antes da data efetiva do renome.
- Operações na data efetiva ou posteriores exigem o ticker atual.
- Se a posição foi totalmente vendida antes do renome, nenhuma conversão é criada.
- Vendas parciais preservam apenas o saldo remanescente para conversão.
- Transações históricas originais permanecem imutáveis.

#### Testes

- Testes do cliente v2 e de resiliência a falhas de rede e payload inválido.
- Testes da validação temporal de tickers no CSV.
- Testes de saldo, custo e venda total/parcial em trocas de ticker.
- Testes do rebuild automático de snapshots.
- Teste frontend do contrato `PATCH` para atualização de carteira.

---

### Concluído — Compliance público e hardening documental (11/07/2026) — #80

#### Documentação

- README, roadmap, changelog e documentos auxiliares passaram a usar termos genéricos para fontes externas de dados.
- Documentos antigos de análise foram atualizados para refletir o estado atual do sistema.
- Prioridades concluídas foram removidas das seções de próximos focos.
- A evolução para provedores configuráveis pelo Superadmin foi registrada no backlog pela issue #127.

#### API pública

- OpenAPI passou a sanitizar descrições, exemplos e valores padrão que identifiquem fornecedores externos.
- Endpoints públicos de cotação passaram a devolver uma origem genérica de dados de mercado.
- Exceções exibidas em modo debug passaram a remover nomes de fornecedores antes da resposta HTTP.
- Logs internos e módulos de integração preservam os identificadores técnicos necessários à operação.

#### Configuração

- Adicionadas variáveis genéricas para token, URL e limites do provedor principal de dados de mercado.
- Adicionada variável genérica para a fonte complementar de dados internacionais.
- Variáveis legadas permanecem aceitas como fallback temporário para evitar quebra de ambientes existentes.
- Quando nomes novos e antigos coexistem, a configuração genérica tem precedência.
- `.env.example` passou a expor somente os nomes genéricos.

#### Testes

- Adicionado teste de compliance dos documentos públicos.
- Adicionado teste de compliance do OpenAPI e dos metadados públicos de cotação.
- Adicionados testes de compatibilidade, fallback e precedência das variáveis de configuração.

---

### Concluído — Resumo, administração e integridade operacional (11/07/2026)

> Entrega consolidada na PR #126 e validada antes do merge em `main`.

#### Backend

- Variação diária por classe separada da rentabilidade acumulada.
- Preços anteriores passaram a compor métricas diárias das posições agrupadas.
- Exclusão de carteira passou a remover explicitamente entidades dependentes.
- Logs de auditoria são preservados com `portfolio_id` desacoplado antes da exclusão.
- Serviços administrativos de usuários completados.
- Validações adicionadas para unicidade, permissões, autoedição e proteção do último superadmin.
- Importação CSV ajustada para tratar corretamente resultados de validação.

#### Frontend

- Menu de ações da tabela de posições passou a usar portal.
- Dropdown deixou de ser cortado pelo contêiner da tabela.
- Cabeçalho das classes passou a exibir variação diária real.
- Modal CSV passou a bloquear confirmação quando houver erros ou avisos impeditivos.
- Caches financeiros são invalidados após importação bem-sucedida.
- Painel administrativo modernizado.

---

### Concluído — Consolidação financeira, CSV, Proventos e Tesouro Direto (10/07/2026)

#### Backend

- Criado serviço canônico de KPIs de carteira.
- Resumo, Patrimônio e Performance passaram a compartilhar os mesmos totais.
- Evolução patrimonial diária e mensal restaurada.
- Manutenção automática de snapshots adicionada ao scheduler.
- Ganho realizado, retorno mensal e retorno de 12 meses corrigidos.
- Importação CSV conectada ao serviço transacional.
- Upload CSV com suporte a UTF-8 BOM, UTF-8 e Latin-1.
- Mensagens conhecidas da importação traduzidas para português.
- Isolamento de carteiras por usuário corrigido.
- Seed histórico de proventos idempotente integrado ao sync diário.
- Catálogo de Tesouro Direto consolidado.

#### Frontend

- KPIs normalizados entre Resumo, Patrimônio e Rentabilidade.
- Gráficos de evolução restaurados.
- Cards de Rentabilidade tiveram rótulos e semântica corrigidos.
- Página Proventos e Rentabilidade passaram a usar a carteira global.

---

## Próximos focos

- Validar o rebuild completo após a documentação e últimas correções de histórico.
- Corrigir consumo de Tesouro nos snapshots.
- Evitar duplicação física de histórico para tickers fracionários.
- Ajustar cards da página Rentabilidade.
- Revisar cards da página Resumo.
- Continuar o motor de eventos corporativos (#129).
- Robustecer Backup/Restore (#83).
- Implementar Google OAuth (#97).
- Avançar em IRPF (#56), Análise (#57) e Janela Global do Ativo (#58).
- Manter provedores configuráveis pelo Superadmin no backlog (#127).
