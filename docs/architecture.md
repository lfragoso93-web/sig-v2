# Arquitetura — SGI v2

> Última atualização: 02/08/2026

## Objetivo

O SGI v2 calcula patrimônio, posição, custo, resultado, proventos e rentabilidade a partir de dados persistidos e contratos canônicos. Provedores externos pertencem a adapters, sincronizadores, jobs ou CLIs operacionais; páginas, KPIs e relatórios não consultam provedores durante o cálculo financeiro.

## Fluxo financeiro principal

```text
CSV / lançamentos manuais
        ↓
transactions + fixed_income_investments + corporate_events
        ↓
projeções canônicas de posição, custo e realizações
        ↓
assets + asset_prices + rate_history + asset_dividends
        ↓
valuation dedicado por classe
        ↓
PortfolioSnapshot + PortfolioClassSnapshot
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / Metas / IRPF
```

## Princípios obrigatórios

### DB-first

Serviços financeiros leem dados persistidos. Chamadas externas não participam do cálculo de posição, custo, resultado ou elegibilidade.

### Contratos financeiros únicos

`summary.v2` e `rentabilidade.v2` são as fontes públicas de leitura consolidada. Posição histórica, custo e resultado realizado são fornecidos por projetores compartilhados, não por reconstruções locais em cada módulo.

### Separação contábil e fiscal

A projeção contábil calcula posição, custo e realização. O IRPF acrescenta apenas semântica fiscal: Day Trade, Swing Trade, isenções, alíquotas, compensações, retenções e apresentação.

### Separação temporal

- valuation intradiário representa o estado atual;
- snapshots representam performance fechada;
- leituras históricas usam data de corte explícita;
- ausência de TWR é `null`, nunca retorno simples disfarçado.

### Idempotência

Seeds, sincronizações e rebuilds devem produzir o mesmo estado lógico sem duplicar preços, eventos, posições ou snapshots.

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

`realized_pnl_projection_reader.py` expõe realizações derivadas da mesma projeção cronológica. Rentabilidade e IRPF devem reconciliar sobre o mesmo conjunto de operações.

### Snapshots

`snapshot_position_projection.py` e `class_snapshot_position_projection.py` alimentam os snapshots sem reconstruções paralelas de posição.

## IRPF

A arquitetura atual separa responsabilidades:

| Serviço | Responsabilidade |
|---|---|
| `irpf_bens_direitos_service.py` | posição e custo em 31/12 via leitor histórico |
| `irpf_tax_service.py` | regras fiscais mensais ainda em caracterização |
| `irpf_report_service.py` | composição e persistência do relatório |
| `irpf_export_service.py` | PDF e CSV |
| `irpf_service.py` | fachada temporária de compatibilidade |

A implementação antiga de Bens e Direitos e o orquestrador duplicado foram removidos. O próximo corte deve caracterizar ganhos de capital mensais antes de migrar regras fiscais.

## Rentabilidade

Resultado realizado, capital líquido aportado e proventos já usam leitores compartilhados. Consumidores remanescentes de posição, custo, patrimônio e PnL não realizado devem ser migrados antes da remoção física da fachada legada (#151).

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

Não existe materialização ativa de direitos por carteira. As tabelas físicas legadas aguardam contração controlada na janela da #158.

## Eventos corporativos

O motor canônico trata splits, grupamentos, bonificações e subscrições independentemente do fornecedor. Eventos preservam identidade, quantidade e custo conforme suas regras; adapters apenas normalizam payloads externos.

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

`/metas` e `/irpf` são aliases temporários com redirect `replace` para compatibilidade.

## Scheduler, seeds e rebuild

O boot não executa sincronização de mercado por padrão. Seeds, sincronizações externas e rebuilds são explicitamente opt-in.

Até o encerramento da Issue #227:

- não importar carteiras reais;
- não criar usuários reais;
- usar bancos descartáveis e fixtures;
- não retomar a certificação da #158;
- não executar automaticamente migrations físicas de contração.

## Qualidade validada

- Backend: `1097 passed`, `22 skipped`, zero warnings.
- Ruff e `compileall`: aprovados.
- Frontend: 86 testes, typecheck, lint e build aprovados.

## Pendências arquiteturais

1. Caracterizar e migrar ganhos de capital mensais do IRPF (#56).
2. Concluir consumidores de Rentabilidade e remover legado (#151).
3. Consolidar eventos corporativos e adapters (#129, #130 e #127).
4. Materializar histórico persistido do IBOV (#150).
5. Implementar TWR dedicado para Tesouro e Renda Fixa (#149).
6. Retomar Proventos, importação e rebuild somente após os gates #158, #216, #226 e #227.
7. Evoluir locks em memória para locks distribuídos antes de múltiplas réplicas.
