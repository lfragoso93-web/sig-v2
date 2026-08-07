# Arquitetura — SGI v2

> Última atualização: 07/08/2026

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
bootstrap/sincronizador de eventos
        ↓
asset_dividends
        ↓
histórico de posições na data de corte
        ↓
direito calculado sob demanda
        ↓
reconhecimento financeiro por data de pagamento
```

Não existe materialização ativa de direitos por carteira. Depois do bootstrap, requests de Proventos não consultam provider.

## Eventos corporativos

O motor canônico trata splits, grupamentos, bonificações e subscrições independentemente do fornecedor. Eventos são coletados no bootstrap/sincronização operacional e persistidos antes de qualquer projeção financeira. Adapters apenas normalizam payloads externos.

A Issue #129 permanece aberta apenas para confirmar, durante a auditoria #247, se ainda existem consumidores ou compatibilidades residuais que precisem de tratamento explícito.

## Transações

`transactions` reflete o contrato financeiro migrado. Criar ou editar transação não dispara coleta externa, onboarding de mercado ou backfill histórico; apenas efeitos locais derivados podem ocorrer.

## Câmbio

`fx_rates` é persistido e DB-first. Requests financeiros leem somente a cobertura persistida. Atualização cambial pertence ao bootstrap/sincronizadores operacionais, não ao cálculo financeiro.

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

A arquitetura alvo distingue três estados:

1. **ambiente não inicializado** — schema disponível, mas dados canônicos ainda não certificados;
2. **bootstrap em execução** — coleta histórica/global idempotente e persistência das séries necessárias;
3. **runtime pronto** — criação/importação de carteiras liberada e consultas funcionais operando DB-first.

O readiness operacional deve refletir essa fronteira. Não basta o processo FastAPI estar de pé: para uso real, o bootstrap precisa estar concluído e validado.

No runtime pronto, o scheduler pode consultar providers apenas para:

- preço intraday;
- preço de fechamento diário.

Não devem existir sincronizações automáticas recorrentes de catálogo, Proventos, eventos, benchmarks, câmbio ou históricos fora de jobs explicitamente controlados para manutenção/correção.

Até o encerramento da Issue #227:

- não importar carteiras reais;
- não criar usuários reais de produção;
- usar bancos descartáveis e fixtures;
- não considerar o ambiente pronto até que o bootstrap canônico seja desenhado, executado e certificado;
- não executar automaticamente migrations físicas de contração.

## Governança arquitetural atual

A ordem canônica é:

1. #247 — concluir auditoria de superfícies e remover consultas externas indevidas;
2. desenhar/validar bootstrap inicial completo e readiness;
3. confirmar pendências reais de #129 e itens necessários de #130/#127;
4. #150 e #149 — performance e benchmarks;
5. #226/#216/#158 — certificação operacional e primeira carga real;
6. #246 + #57 — macroprojeto Metas + Análise.

## Qualidade validada

Checkpoint certificado localmente no HEAD `08414af3a7b570ae9753e83ba5eecf2c17f20e42`:

- build Docker aprovado;
- 7 testes do checkpoint de auditoria aprovados;
- `compileall` aprovado;
- import integral de `app.main` aprovado;
- working tree limpa.

## Pendências arquiteturais

1. Concluir auditoria global de serviços, routers, endpoints, duplicações e legado remanescente (#247).
2. Remover providers de todas as superfícies funcionais que não sejam preço intraday/fechamento.
3. Desenhar e certificar bootstrap inicial completo antes de liberar carteiras reais.
4. Confirmar e resolver somente pendências reais de eventos corporativos/provedores (#129/#130/#127).
5. Materializar histórico persistido do IBOV (#150).
6. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
7. Retomar Proventos, importação e rebuild apenas após #226/#216/#158/#227.
8. Iniciar #246 + #57 somente depois da estabilização e promoção da base.
