# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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