# Inventário de consumidores — deriva Alembic × ORM

Issue principal: #241

## Objetivo

Registrar consumidores e duplicações antes de qualquer migration corretiva. Nenhuma decisão destrutiva deve ser tomada apenas com base no `alembic check`.

## Configurações

### `system_configs`

- modelo atual: `app.models.system_config.SystemConfig`;
- tabela já presente no schema migrado;
- possui conjunto explícito de `DEFAULT_CONFIGS`;
- finalidade declarada: configurações editáveis pelo SuperAdmin;
- contrato inclui `created_at` e `updated_at` pelo `TimestampMixin`.

### `app_config`

- modelo atual: `app.models.config.AppConfig`;
- estrutura chave-valor praticamente equivalente a `system_configs`;
- tabela ausente das migrations atuais;
- não deve receber migration própria antes de comprovar consumidor exclusivo;
- decisão preliminar: provável duplicação legada de `system_configs`.

### Gate de decisão

Antes de criar `app_config` no banco:

1. localizar consumidores reais de `AppConfig`;
2. comparar semântica de `updated_at`, visibilidade pública e defaults;
3. migrar consumidores para `SystemConfig` quando equivalentes;
4. remover o modelo duplicado somente após regressões e ausência comprovada de consumidores.

## IRPF

### `irpf_reports`

- modelo atual: `app.models.irpf.IRPFReport`;
- relacionamento ativo em `Portfolio.irpf_reports`;
- tabela ausente das migrations atuais;
- armazenamento proposto como JSON serializado por carteira/ano;
- não deve receber migration antes de alinhamento com a Issue #56 e o contrato canônico anual.

### `irpf_records` e `irpf_losses`

- tabelas presentes no schema migrado;
- ausentes do agregador ORM atual;
- representam apuração mensal e prejuízos acumulados por usuário/mercado;
- não podem ser removidas automaticamente enquanto consumidores, exportações e compatibilidade histórica não forem inventariados.

### Decisão preliminar

`irpf_reports` não é substituto demonstrado de `irpf_records`/`irpf_losses`. Os contratos têm granularidades e identidades diferentes:

- relatório anual por carteira;
- apuração mensal e prejuízos por usuário/mercado.

Qualquer consolidação deve ser coordenada pela #56 e feita por expansão/migração explícita, nunca por autogenerate destrutivo.

## Metas

### `goals`

- modelo atual em `app.models.goal.Goal`;
- `Portfolio` mantém relacionamento `goals`;
- o bloco `TYPE_CHECKING` de `Portfolio` referencia incorretamente `app.models.goals`, módulo inexistente;
- migrations e modelo divergem em tipos, colunas e constraints.

### `goal_allocations`

- tabela presente no schema migrado;
- ausente do ORM atual;
- não deve ser removida sem inventário de consumidores e decisão sobre metas de alocação.

## Câmbio

### `fx_rates`

- tabela presente no schema migrado;
- ausente do ORM atual;
- não deve ser removida por ausência no `MetaData`;
- decisão depende do inventário de consumidores de conversão cambial, valuation e ativos no exterior.

## Próximos blocos seguros

1. corrigir apenas o import de tipagem `app.models.goals` → `app.models.goal`;
2. adicionar gates para impedir migration de `app_config` sem consumidor exclusivo comprovado;
3. adicionar gates para impedir tratamento de `irpf_reports` como substituto automático das tabelas mensais;
4. inventariar consumidores de `fx_rates` e `goal_allocations` antes de qualquer alteração de schema.
