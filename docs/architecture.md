# Arquitetura — SGI v2

> Última atualização: 07/08/2026

## Objetivo

O SGI v2 calcula patrimônio, posição, custo, resultado, proventos, rentabilidade e IRPF a partir de dados persistidos e contratos canônicos. Provedores externos pertencem a adapters, sincronizadores, jobs ou CLIs operacionais; páginas, KPIs e relatórios não consultam provedores durante o cálculo financeiro.

## Fluxo financeiro principal

```text
CSV / lançamentos manuais
        ↓
transactions + fixed_income_investments + corporate_events
        ↓
projeções canônicas de posição, custo e realizações
        ↓
assets + asset_prices + rate_history + fx_rates + asset_dividends
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

Metas não integra, neste momento, o conjunto de contratos financeiros estabilizados. O domínio será redesenhado em conjunto com Análise de Carteira (#246 + #57).

## Princípios obrigatórios

### DB-first

Serviços financeiros leem dados persistidos. Chamadas externas não participam do cálculo de posição, custo, resultado, elegibilidade ou câmbio durante requests financeiros.

### Contratos financeiros únicos

`summary.v2` e `rentabilidade.v2` são as fontes públicas de leitura consolidada. Posição histórica, custo e resultado realizado são fornecidos por projetores compartilhados, não por reconstruções locais em cada módulo.

### Alembic como autoridade de schema

- O startup não cria tabelas paralelamente ao Alembic.
- `Base.metadata` deve refletir os contratos estabilizados produzidos pelas migrations.
- Autogenerate monolítico não é mecanismo de correção arquitetural.
- Divergências devem ser classificadas e tratadas por domínio, com migrations pequenas, defensivas e reversíveis quando DDL for realmente necessário.
- Módulos incompletos não devem ter seu schema cristalizado apenas para silenciar `alembic check`.

### Separação contábil e fiscal

A projeção contábil calcula posição, custo e realização. O IRPF acrescenta semântica fiscal: Day Trade, Swing Trade, isenções, alíquotas, compensações, retenções e apresentação.

### Separação temporal

- valuation intradiário representa o estado atual;
- snapshots representam performance fechada;
- leituras históricas usam data de corte explícita;
- ausência de TWR é `null`, nunca retorno simples disfarçado.

### Idempotência

Seeds, sincronizações, migrations e rebuilds devem produzir o mesmo estado lógico sem duplicar preços, eventos, posições ou snapshots.

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
provedores normalizados
        ↓
asset_dividends
        ↓
histórico de posições na data de corte
        ↓
direito calculado sob demanda
        ↓
reconhecimento financeiro por data de pagamento
```

Não existe materialização ativa de direitos por carteira. O MetaData representa os índices físicos definidos pelas migrations canônicas.

## Eventos corporativos

O motor canônico trata splits, grupamentos, bonificações e subscrições independentemente do fornecedor. Eventos preservam identidade, quantidade, custo, JSONB e constraints de identidade conforme a migration canônica; adapters apenas normalizam payloads externos.

## Transações

`transactions` reflete o contrato financeiro migrado: precisão `NUMERIC`, `fees NOT NULL`, `notes TEXT`, timestamps físicos e todos os índices históricos. Serviços consumidores devem respeitar esse contrato e não criar representações financeiras paralelas.

## Câmbio

`fx_rates` é persistido e DB-first. O endpoint `/usd-brl` lê exclusivamente a última cobertura persistida; nenhuma chamada externa ou fallback fixo ocorre no request. `FxRate` participa de `Base.metadata` com constraints e índices alinhados às migrations.

## Metas e Análise de Carteira

O módulo `goals` é uma exceção arquitetural consciente na convergência Alembic/ORM:

- a tabela histórica está preservada;
- o ORM, schemas Pydantic e service atuais não formam um contrato funcional coerente;
- nenhuma migration deve ser criada apenas para limpar o diff remanescente do `alembic check`;
- o redesenho será conduzido pela #246 em conjunto com #57;
- a nova arquitetura deve decidir taxonomia, KPIs calculados versus persistidos, relação com `portfolio_class_targets`, histórico e projeções antes de qualquer DDL definitivo.

A rota `/carteira/metas` pode existir como superfície atual, mas não transforma o domínio subjacente em contrato canônico estabilizado.

## Navegação de carteira

Módulos dependentes da carteira selecionada ficam sob `/carteira`:

```text
/carteira
├── patrimonio
├── rentabilidade
├── transacoes
├── proventos
├── metas
├── irpf
└── configuracoes
```

`/metas` e `/irpf` permanecem aliases temporários com redirect `replace` para compatibilidade.

## Scheduler, seeds e rebuild

O boot não executa sincronização de mercado por padrão. Seeds, sincronizações externas e rebuilds são explicitamente opt-in.

Até o encerramento da Issue #227:

- não importar carteiras reais sem autorização;
- não criar usuários reais;
- usar bancos descartáveis e fixtures;
- não retomar a certificação da #158 fora dos gates vigentes;
- não executar automaticamente migrations físicas de contração.

## Qualidade validada

No checkpoint estrutural de 07/08/2026:

- build Docker aprovado;
- `compileall` aprovado;
- suíte estrutural final: 15 testes aprovados;
- import integral de `app.main` aprovado;
- consumers legados removidos e protegidos por gates;
- Alembic/ORM convergidos fora de `goals`.

## Pendências arquiteturais

1. Encerrar formalmente a #241 sem alterar `goals`.
2. Fazer auditoria global de serviços, routers, endpoints, duplicações e legado restante.
3. Consolidar consumidores remanescentes de eventos corporativos e adapters (#129, #130 e #127), se a auditoria ainda encontrar pendências.
4. Materializar histórico persistido do IBOV (#150).
5. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
6. Retomar Proventos, importação e rebuild somente após os gates #158, #216, #226 e #227.
7. Iniciar o macroprojeto Metas + Análise de Carteira (#246 + #57) apenas após a estabilização definitiva da base.
8. Evoluir locks em memória para locks distribuídos antes de múltiplas réplicas.
