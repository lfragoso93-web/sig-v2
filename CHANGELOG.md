# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — alinhamento de índices Alembic/MetaData (06/08/2026)

- `asset_prices` passou a representar no ORM o índice físico `idx_ap_asset_ts (asset_id, timestamp DESC)`.
- `audit_logs` deixou de pedir índices simples inexistentes em `user_id`/`portfolio_id` e passou a representar os índices compostos com `created_at DESC`.
- `portfolio_snapshots` passou a representar corretamente `idx_ps_portfolio_date_desc`.
- `portfolio_positions` passou a preservar `idx_pp_portfolio` e deixou de pedir índice simples inexistente em `asset_id`.
- `portfolio_class_targets` passou a representar `idx_pct_portfolio`, criado pela migration de performance.
- Adicionados gates para impedir regressão desses contratos de índice.
- Nenhuma migration, DDL ou dado foi alterado nestes alinhamentos.

### Removido — schema mensal legado vazio de IRPF (06/08/2026)

- Adicionadas migrations separadas para `irpf_losses` e `irpf_records`, ambas sem consumidores runtime e vazias na evidência PostgreSQL local.
- Cada upgrade retorna quando a tabela já não existe e bloqueia a contração caso encontre qualquer linha.
- Cada downgrade restaura o contrato original, FK para `users.id` com `ON DELETE CASCADE`, defaults e índices históricos.
- O enum compartilhado `irpfmarket` é preservado e não é removido por nenhuma das duas migrations.
- A contração foi coordenada pela Issue #242, separada dos contratos financeiros compartilhados da #241.

### Removido — contrato legado vazio `goal_allocations` (06/08/2026)

- Adicionada migration isolada para remover `goal_allocations`, tabela sem consumidor runtime e vazia na evidência local.
- O upgrade é bloqueado quando existir qualquer linha, impedindo descarte silencioso de dados.
- O downgrade restaura tabela, FK `goal_allocations_goal_id_fkey` com `ON DELETE CASCADE` e índice `ix_goal_allocations_id`.
- `irpf_records` e `irpf_losses` permanecem fora desta contração e continuam preservadas.

### Adicionado — fixture sintética transacional para contratos legados (06/08/2026)

- Adicionada fixture PostgreSQL nativa para `irpf_records`, `irpf_losses` e `goal_allocations`, incluindo seus pais `users`, `portfolios` e `goals`.
- A fixture usa `ON_ERROR_STOP`, valida exatamente uma linha por contrato e termina obrigatoriamente em `ROLLBACK`.
- Adicionados gates que proíbem `COMMIT`, `DROP TABLE` e `TRUNCATE`, além de proteger o uso de variáveis `psql` e as três asserções de cardinalidade.
- Nenhuma migration, DDL persistente, tabela ou dado real foi alterado.

### Protegido — fronteira do schema mensal legado de IRPF (06/08/2026)

- `irpf_records` e `irpf_losses` foram classificados como contratos migrados legados, preservados até evidência de dados e decisão destrutiva explícita.
- Adicionado gate que confirma sua presença na migration inicial e impede consumidores runtime em `app/models`, `app/routers` e `app/services`.
- Proibida a reintrodução de modelos ORM mensais apenas para silenciar o `alembic check`.
- Contagem de linhas, inventário de FKs e fixture sintética passam a ser pré-requisitos para eventual remoção.
- Nenhuma migration, DDL, tabela ou dado foi alterado.

### Corrigido — contrato `fx_rates` consolidado no MetaData (06/08/2026)

- O inventário de deriva deixou de classificar `fx_rates` como schema ausente do MetaData: `FxRate` já está registrado no agregador `app.models` e participa de `Base.metadata`.
- Congelados como canônicos `UNIQUE (pair, rate_date)`, o índice ascendente `ix_fx_rates_pair_date` e o índice descendente `idx_fx_pair_date_desc`.
- Adicionados gates contra duplicação de modelo ou migration motivada apenas por diff histórico.
- Nenhuma migration, DDL, tabela ou dado foi alterado.

### Corrigido — geração legada de IRPF integralmente read-only (06/08/2026)

- `irpf_report_service.py` deixou de importar o modelo removido `IRPFReport` e de consultar, inserir, atualizar ou executar `commit` sobre `irpf_reports`.
- `generate_irpf_report` preserva sua assinatura pública e compõe `IRPFReportOut` exclusivamente em memória a partir dos leitores fiscais existentes.
- O gate de consumidores removidos passou a inspecionar imports por AST, distinguindo corretamente o modelo ORM `IRPFReport` do DTO válido `IRPFReportOut`.
- Nenhuma migration, tabela ou dado foi alterado.

### Corrigido — varredura global de consumidores removidos no startup (06/08/2026)

- O router legado de IRPF deixou de importar `IRPFReport` e de consultar o modelo órfão removido.
- O endpoint `/{portfolio_id}/irpf/{year}` preserva o contrato HTTP e o parâmetro `refresh`, mas sempre projeta o relatório read-only em memória por `generate_irpf_report`.
- Adicionado gate global que percorre todo `backend/app/**/*.py` contra imports de `app.models.irpf`/`IRPFReport` e `app.models.config`/`AppConfig`.
- Adicionado teste de importação completa de `app.main`, cobrindo todos os routers e serviços carregados no startup antes da próxima execução Docker.
- Nenhuma migration, tabela ou dado foi alterado.

### Corrigido — serviço de configurações migrado para `SystemConfig` (06/08/2026)

- `config_service.py` deixou de importar o modelo removido `AppConfig` e passou a operar exclusivamente sobre `SystemConfig`/`system_configs`.
- Preservados os fluxos de leitura, booleanos, upsert individual, listagem pública e atualização em lote usados pelo painel administrativo.
- Adicionado gate que proíbe novos consumidores de `app.models.config` e de `AppConfig` no serviço de configurações.
- Nenhuma migration, tabela ou dado foi alterado; a correção elimina uma falha de import que impedia o backend de iniciar.

### Corrigido — startup usa somente Alembic como autoridade de schema (06/08/2026)

- Removido do `entrypoint.sh` o bootstrap paralelo que executava `table.create(checkfirst=True)` para tabelas opcionais do ORM.
- Eliminado o import obsoleto de `app.models.irpf`, que mantinha o backend em ciclo de restart após a remoção do modelo órfão `IRPFReport`.
- `CorporateEvent` e `Goal` continuam disponíveis exclusivamente pelas migrations existentes; o entrypoint não cria mais tabelas fora da cadeia Alembic.
- Adicionado gate arquitetural que proíbe `table.create`, `OPTIONAL_TABLES`, `checkfirst=True` e imports do modelo IRPF removido no startup.
- Nenhuma migration, tabela ou dado foi alterado neste bloco.

### Removido — modelo órfão `IRPFReport` (06/08/2026)

- Inventariados `IRPFReport`, `irpf_reports`, `irpf_records` e `irpf_losses` em coordenação com as Issues #56 e #241.
- Confirmado que os endpoints e exports canônicos de IRPF são read-only e não consultam nem persistem `IRPFReport`.
- `IRPFReport` foi removido do agregador `app.models`, do relacionamento de `Portfolio` e do arquivo `backend/app/models/irpf.py`.
- O projeto não criará a tabela `irpf_reports` apenas para silenciar o `alembic check`.
- `irpf_records` e `irpf_losses` permanecem preservadas como schema legado mensal até fixture sintética, inventário de dados e decisão destrutiva explícita.
- Nenhuma migration, DDL, tabela ou dado foi alterado neste bloco.

### Removido — modelo duplicado `AppConfig` (06/08/2026)

- `AppConfig` e `app_config` foram classificados como duplicação histórica de `SystemConfig`/`system_configs`.
- O modelo duplicado foi removido do agregador `app.models` e do código-fonte.
- Nenhuma migration, tabela ou dado foi alterado neste bloco.
