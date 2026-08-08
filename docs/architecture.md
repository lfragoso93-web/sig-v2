# Arquitetura — SGI v2

> Última atualização: 08/08/2026

## Objetivo

O SGI v2 calcula patrimônio, posição, custo, resultado, proventos, rentabilidade e IRPF a partir de dados persistidos e contratos canônicos. Provedores externos pertencem ao bootstrap inicial e aos sincronizadores operacionais de preço; páginas, KPIs, relatórios e cálculos financeiros não consultam providers diretamente.

## Fluxo financeiro principal

```text
bootstrap inicial certificado
        ↓
assets + asset_prices + rate_history + fx_rates + asset_dividends + corporate_events
        ↓
transactions + fixed_income_investments
        ↓
projeções canônicas de posição, custo e realizações
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

Metas e Análise de Carteira não integram, neste momento, o conjunto de contratos funcionais estabilizados. O redesenho será conduzido em conjunto por #246 + #57 somente após a estabilização definitiva da base.

## Princípios obrigatórios

### Bootstrap-first + DB-first

Antes de existir uso real, o ambiente deve executar um bootstrap idempotente e certificável que carregue no banco todo o conjunto necessário ao funcionamento do sistema:

- catálogo de ativos e metadados;
- histórico de preços;
- Proventos globais;
- eventos corporativos;
- Tesouro Direto e histórico associado;
- benchmarks e taxas;
- câmbio;
- demais séries auxiliares necessárias aos contratos canônicos.

A aplicação só deve ser considerada pronta para criação/importação de carteiras reais depois da conclusão e validação desse bootstrap.

Após o bootstrap:

- serviços financeiros leem dados persistidos;
- busca, detalhes, posições, relatórios, IRPF, Proventos e rentabilidade não consultam provider;
- consultas externas recorrentes ficam restritas a **preço intraday** e **preço oficial/de fechamento do dia**;
- preços obtidos externamente devem ser persistidos antes de alimentar contratos financeiros;
- nenhuma mutação comum de usuário dispara seed, onboarding, backfill histórico ou coleta de eventos.

### Cobertura histórica por domínio

Não existe uma data inicial global arbitrária para o bootstrap. Cada domínio define a maior cobertura válida suportada por sua fonte canônica:

- USD-BRL: `1994-07-01`, início do Real, via PTAX oficial;
- Proventos: `1970-01-01`, limite técnico atual do histórico Yahoo complementar usado pelo adapter estrito;
- preços, Tesouro, benchmarks e eventos mantêm suas próprias regras de cobertura.

Essa separação evita que uma limitação de um provider reduza silenciosamente a profundidade dos demais domínios.

### Contratos financeiros únicos

`summary.v2` e `rentabilidade.v2` são as fontes públicas de leitura consolidada. Posição histórica, custo e resultado realizado são fornecidos por projetores compartilhados, não por reconstruções locais em cada módulo.

### Alembic como autoridade de schema

- O startup não cria tabelas paralelamente ao Alembic.
- `Base.metadata` deve refletir contratos estabilizados produzidos pelas migrations.
- Autogenerate monolítico não é mecanismo de correção arquitetural.
- Divergências devem ser classificadas e tratadas por domínio.
- Módulos incompletos não devem ter schema cristalizado apenas para silenciar `alembic check`.

### Separação contábil e fiscal

A projeção contábil calcula posição, custo e realização. O IRPF acrescenta semântica fiscal: Day Trade, Swing Trade, isenções, alíquotas, compensações, retenções e apresentação.

### Separação temporal

- preço intraday representa estado corrente e pode vir de sincronizador externo dedicado;
- preço de fechamento diário é coletado externamente e persistido como referência oficial do dia;
- snapshots representam performance fechada;
- leituras históricas usam data de corte explícita;
- ausência de TWR é `null`, nunca retorno simples disfarçado.

### Idempotência

Bootstrap, seeds, sincronizações, migrations e rebuilds devem produzir o mesmo estado lógico sem duplicar preços, eventos, posições ou snapshots.

### Qualidade explícita

Cobertura parcial, preços ausentes, retornos estimados, fonte e data de referência permanecem visíveis. Ausência ou falha não vira zero silenciosamente.

### Tempo UTC explícito

- serviços operacionais usam UTC timezone-aware;
- colunas `DateTime(timezone=False)` usam UTC naive por helper explícito;
- `datetime.utcnow()` não é permitido no runtime.

## Projeções canônicas

### Posição e custo

`position_timeline_projection.py` é o núcleo cronológico puro. Readers de banco carregam transações e eventos e aplicam a data de corte.

```text
transactions + corporate_events
        ↓
position_timeline_projection
        ↓
historical_position_projection_reader
        ↓
posições abertas + custo + timelines
```

### Resultado realizado

`realized_pnl_projection_reader.py` expõe realizações derivadas da mesma projeção cronológica. Rentabilidade e IRPF reconciliam sobre o mesmo conjunto de operações.

### Snapshots

`snapshot_position_projection.py` e `class_snapshot_position_projection.py` alimentam snapshots sem reconstruções paralelas de posição. O MetaData de snapshots representa índices, comentários e timestamps físicos da cadeia Alembic canônica.

## IRPF

A arquitetura atual separa responsabilidades e não persiste `IRPFReport` legado:

| Serviço | Responsabilidade |
|---|---|
| `irpf_bens_direitos_service.py` | posição e custo em 31/12 via leitor histórico |
| `irpf_tax_service.py` | regras fiscais mensais canônicas |
| `irpf_report_service.py` | composição read-only do relatório |
| `irpf_export_service.py` | PDF e CSV a partir dos contratos canônicos |

`app.models.irpf`, `IRPFReport`, `irpf_records` e `irpf_losses` não participam do runtime canônico. Consumers removidos são protegidos por gates estruturais.

## Rentabilidade

A fachada legada foi removida. Resultado realizado, capital líquido aportado, proventos, posição e patrimônio usam contratos compartilhados; invalidação de cache está isolada no serviço canônico de cache.

## Proventos

Eventos pertencem ao ativo e são persistidos exclusivamente em `asset_dividends`.

```text
system-bootstrap.v3 / seed estrito autorizado
        ↓
asset_dividends
        ↓
histórico de posições na data de corte
        ↓
direito calculado sob demanda
        ↓
reconhecimento financeiro por data de pagamento
```

O bootstrap reutiliza `pre-prod-dividends-seed.v2`, com adapters estritos BRAPI + Yahoo e identidade auditável compartilhada. A presença da etapa no orquestrador não autoriza execução real: sem `SGI_BOOTSTRAP_ENABLE_DIVIDENDS=true`, ela falha antes de consultar providers, e a autorização operacional continua pertencendo à #226.

Não existe materialização ativa de direitos por carteira. Depois do bootstrap, requests de Proventos não consultam provider.

## Eventos corporativos

O motor canônico trata splits, grupamentos, bonificações e subscrições independentemente do fornecedor. Eventos pertencem ao ativo, são persistidos em `corporate_events` e alimentam projeções históricas sem mutar transações originais.

A Issue #129 permanece aberta para concluir a auditoria residual e governar a integração deste domínio ao bootstrap global. O próximo estágio deve reutilizar `corporate_event_service.py` e os normalizadores existentes, sem criar nova lógica de provider no orquestrador.

## Transações

`transactions` reflete o contrato financeiro migrado. Criar ou editar transação não dispara coleta externa, onboarding de mercado ou backfill histórico; apenas efeitos locais derivados podem ocorrer.

## Câmbio

`fx_rates` é persistido e DB-first. Requests financeiros leem somente a cobertura persistida.

O `system-bootstrap.v2+` integra USD-BRL reutilizando o estágio auditável da #217:

- PTAX oficial do BCB;
- par único `USD-BRL`;
- cobertura desde `1994-07-01`;
- advisory lock;
- inspeção antes/depois;
- transação controlada;
- identidade `run_id + stable-15jun + SHA`.

Nenhum fallback BRAPI/AwesomeAPI/fixo participa deste estágio certificado.

## Metas e Análise de Carteira

O módulo `goals` é uma exceção arquitetural consciente:

- a tabela histórica está preservada;
- ORM, schemas Pydantic e service atuais não formam contrato funcional coerente;
- nenhuma migration deve ser criada apenas para limpar o diff remanescente do `alembic check`;
- o redesenho será conduzido pela #246 em conjunto com #57;
- a nova arquitetura deve decidir taxonomia, KPIs calculados versus persistidos, relação com `portfolio_class_targets`, histórico e projeções antes de DDL definitivo.

## Navegação de carteira

Módulos dependentes da carteira selecionada ficam sob `/carteira`. Aliases temporários devem ser eliminados somente após comprovação de consumidores durante a #247.

## Bootstrap, scheduler e readiness

A porta única atual é `run_system_bootstrap()` sob contrato `system-bootstrap.v3`.

A arquitetura distingue três estados:

1. **ambiente não inicializado** — schema disponível, mas dados canônicos ainda não certificados;
2. **bootstrap em execução** — coleta histórica/global idempotente e persistência das séries necessárias;
3. **runtime pronto** — criação/importação de carteiras liberada e consultas funcionais operando DB-first.

O bootstrap carrega contexto auditável único com `run_id`, branch `stable-15jun` e SHA completo. O disparo administrativo exige esse SHA; startup automático pode recebê-lo por `SGI_BOOTSTRAP_COMMIT_SHA`.

Etapas registradas no v3:

1. `asset_catalog`;
2. `treasury_catalog`;
3. `treasury_reconciliation`;
4. `treasury_history`;
5. `asset_price_history`;
6. `benchmarks`;
7. `fx_rates`;
8. `asset_dividends` — explicitamente gated pela #226.

Eventos corporativos ainda precisam ser adicionados como estágio explícito antes da certificação integral.

O readiness operacional reflete essa fronteira. Não basta o processo FastAPI estar de pé: para uso real, o bootstrap precisa estar concluído e validado. `ready_for_real_data` permanece `false` durante a consolidação estrutural.

No runtime pronto, o scheduler pode consultar providers apenas para:

- preço intraday;
- preço de fechamento diário.

Não devem existir sincronizações automáticas recorrentes de catálogo, Proventos, eventos, benchmarks, câmbio ou históricos fora de jobs explicitamente controlados para manutenção/correção.

Até o encerramento da Issue #227:

- não importar carteiras reais;
- não criar usuários reais de produção;
- usar bancos descartáveis e fixtures;
- não considerar o ambiente pronto até que o bootstrap canônico seja integralmente executado e certificado;
- não executar automaticamente migrations físicas de contração.

## Governança arquitetural atual

A ordem canônica é:

1. validar localmente `system-bootstrap.v3` e o gate estrutural de Proventos;
2. integrar eventos corporativos sob #129 sem duplicar adapters/providers;
3. concluir #247/#248/#250 e certificar a fronteira provider/bootstrap;
4. #150 e #149 — performance e benchmarks;
5. #226/#216/#158 — certificação operacional e primeira carga real;
6. #246 + #57 — macroprojeto Metas + Análise.

## Qualidade validada

Último checkpoint certificado localmente pelo usuário no HEAD `0e8d96c081a0e788a9edcf69901a134b29b7f696`:

- build Docker aprovado;
- 22 testes do checkpoint de bootstrap/FX/readiness aprovados;
- `compileall` aprovado;
- import integral de `app.main` aprovado;
- HEAD local igual ao esperado.

O `system-bootstrap.v3` com etapa de Proventos foi implementado depois desse checkpoint e ainda precisa de validação local.

## Pendências arquiteturais

1. Validar localmente o `system-bootstrap.v3` e o gate de Proventos.
2. Incorporar eventos corporativos ao bootstrap global sob #129.
3. Concluir auditoria global de serviços, routers, endpoints, duplicações e legado remanescente (#247).
4. Certificar cobertura/idempotência dos domínios obrigatórios e somente então liberar readiness real.
5. Materializar histórico persistido do IBOV (#150).
6. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
7. Retomar execução real de Proventos, importação e rebuild apenas sob #226/#216/#158/#227.
8. Iniciar #246 + #57 somente depois da estabilização e promoção da base.