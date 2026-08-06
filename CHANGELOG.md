# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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

- Confirmada ausência de consumidores ativos de `AppConfig` e de `app.models.config`.
- `SystemConfig` permanece como contrato migrado e canônico para configurações do sistema.
- `AppConfig` foi removido do agregador `app.models` e o arquivo `backend/app/models/config.py` foi eliminado.
- Gates arquiteturais agora exigem a inexistência física do modelo duplicado e impedem seu retorno ao `MetaData`.
- Nenhuma migration, DDL, tabela ou dado foi alterado; o objetivo é eliminar uma operação falsa de criação de `app_config` no `alembic check`.

### Alterado — consumidor USD/BRL migrado para DB-first (06/08/2026)

- Criado `fx_rate_reader.py` para ler a última cotação persistida por par diretamente de `fx_rates`, preservando `Decimal`, data de referência e ausência explícita.
- O endpoint `/usd-brl` deixou de chamar provider durante request e agora depende de sessão assíncrona do banco.
- O campo público `rate` e o identificador `pair=USDBRL` foram preservados; `rate_date` e `source=persisted_fx_rates` foram adicionados para rastreabilidade.
- Quando não existe cobertura persistida, o endpoint retorna indisponibilidade explícita em vez de inventar uma cotação.
- A integração legada `app.integrations.fx_rate`, incluindo o fallback fixo `5.40`, foi removida.
- Gates arquiteturais agora exigem leitura DB-first, inexistência do módulo legado e ausência de `httpx`/fallback no router.
- Nenhum seed, provider, migration ou dado real foi executado neste bloco.

### Adicionado — inventário e gates da deriva Alembic/ORM (06/08/2026)

- Criada a Issue #241 para tratar separadamente a deriva global entre o schema produzido pelas migrations e o `MetaData` ORM atual.
- Versionados inventários de deriva, consumidores e decisões provisórias para `app_config`, `system_configs`, `irpf_reports`, `irpf_records`, `irpf_losses`, `fx_rates`, `goal_allocations` e contratos compartilhados.
- Adicionada política executável que proíbe autogenerate monolítico, remoção baseada apenas na ausência do `MetaData` e reintrodução artificial de modelos ORM.
- Gates focados passaram a proteger decisões de configuração, IRPF, câmbio e metas dentro da imagem Docker, sem depender da pasta raiz `docs/`.
- PostgreSQL vazio alcançou `20260731_corp_event_catalog (head)` e a segunda execução de `alembic upgrade head` foi idempotente.
- `alembic check` permanece bloqueado por dívida estrutural histórica e será reduzido por domínio, um contrato por commit.

### Classificado — schema legado de metas (06/08/2026)

- O fluxo atual de metas usa somente `goals` por carteira, com frontend, hooks, router, service e KPIs canônicos.
- Nenhum consumidor runtime comprovado usa `goal_allocations`.
- A tabela permanece preservada até fixture sintética e decisão explícita sobre dados e compatibilidade; não será reintroduzida no ORM apenas para silenciar `alembic check`.

### Corrigido — import de tipagem do modelo Goal (06/08/2026)

- O `TYPE_CHECKING` de `Portfolio` passou de `app.models.goals` inexistente para `app.models.goal`.
- A alteração não modifica runtime, schema ou regra financeira.

### Alterado — documentação viva pós-promoções estruturais (06/08/2026)

- README e ROADMAP deixaram de tratar a abertura das PRs estruturais como pendente.
- Registrado que as PRs #237 e #240 já foram mergeadas na `main`.
- O próximo gate foi atualizado para convergência Alembic/ORM e certificação dos consumidores de eventos corporativos.

### Adicionado — bootstrap canônico auditável de ativos (05/08/2026)

- Estruturado o pipeline neutro por capacidades independentes para catálogo, preços, Proventos, eventos corporativos e cobertura.
- Adicionados estados explícitos por etapa (`planned`, `executed`, `blocked`, `failed`) e validação pré-execução de duplicidades, ordem inválida e ciclos de dependência.
- Criados planejamento read-only, envelope JSON versionado e comparadores offline de planos e relatórios.
- Planejamento e execução simulada agora aceitam identidade auditável por `run_id`, branch e commit SHA.
- A CLI `plan_asset_bootstrap` permanece isolada de fixtures de teste, providers, ORM, sessões e operações de escrita por regressões arquiteturais específicas.
- Nenhuma capacidade produtiva de provider, persistência, seed ou rebuild foi conectada; o gate operacional da Issue #227 permanece vigente.

### Removido — fachada legada de Rentabilidade (05/08/2026)

- `backend/app/services/rentabilidade_service.py` foi removido após a migração completa de consumidores produtivos para os contratos e serviços canônicos.
- A invalidação das chaves `rent:*` foi isolada em `rentabilidade_cache_service.py` e permanece best-effort nos fluxos de transação, importação CSV e reconstrução de snapshots.
- Testes acoplados exclusivamente ao serviço órfão foram removidos; o gate arquitetural agora exige a inexistência física do arquivo e impede novos imports do módulo legado.
- A suíte backend foi validada duas vezes após a remoção, com `1246 passed` e `22 skipped`, além de `compileall`, Flake8 e build Docker aprovados.
- Nenhum endpoint, schema, migration ou fórmula financeira canônica foi alterado neste macrobloco.

### Concluído — módulo IRPF canônico (04/08/2026)

- Consolidada a apuração anual canônica de Day Trade e Swing Trade, incluindo
  isenção mensal, compensação segregada de prejuízos, IRRF e acumulação de DARF
  abaixo do mínimo legal.
- Publicados contratos versionados para apuração anual, Bens e Direitos,
  Rendimentos e Ganhos de Capital, todos autorizados e isolados por carteira.
- A `IRPFPage.tsx` passou a consumir exclusivamente hooks canônicos e deixou de
  carregar `IRPFReportOut`, `refreshKey` e o relatório completo legado.
- PDF e CSV passaram a ser compostos diretamente por `IrpfCanonicalExport`, sem
  leitura de `IRPFReport`, persistência fiscal legada ou fallback para
  `generate_irpf_report`.
- O endpoint completo legado foi mantido apenas para compatibilidade externa;
  a fachada Python histórica adapta contratos em memória sem reintroduzir
  consultas ou persistência nos fluxos públicos canônicos.
- A cobertura final validou 93 testes frontend e 1265 testes backend, com 22
  skips documentados, além de Ruff, typecheck, ESLint, build e compileall.
- README, ROADMAP, documentação técnica e Issue #56 foram sincronizados; a única
  pendência funcional restante é a validação com carteira real representativa.
