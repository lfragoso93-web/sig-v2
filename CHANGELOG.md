# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

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

### Adicionado — caracterização de ganhos mensais do IRPF (03/08/2026)

- Ampliado o baseline fiscal de Day Trade para compra e venda no mesmo dia,
  múltiplas vendas, custos operacionais e agregação mensal.
- Congelado em teste, sem correção de regra, o comportamento que classifica a
  venda inteira como Day Trade quando há posição anterior e casamento
  intradiário apenas parcial.
- O inventário e o plano de migração registram os cenários já cobertos e os
  gates restantes antes da integração com os projetores canônicos.
- A caracterização fiscal específica foi separada da suíte da fachada e agora
  cobre saldo Swing no dia seguinte, operações intercaladas, isolamento por
  ticker e coexistência mensal de resultados Day Trade e Swing Trade.
- A matriz passou a cobrir as fronteiras de R$ 20 mil da isenção mensal,
  agregação entre tickers, classes não isentas e a ausência vigente de
  transporte de prejuízo Swing; helpers compartilhados eliminam duplicação na
  infraestrutura desses testes.
- Foram congelados ainda a ausência de transporte de prejuízo Day Trade, o BDR
  no grupo atual de isenção, retenções zeradas e a agregação cruzada que pode
  reduzir indevidamente a base de uma classe tributável com vendas isentas.
- O baseline passou a registrar venda acima da posição, conversão cambial por
  transação, fallback USD/BRL `1.0` e ausência de eventos corporativos na
  reconstrução fiscal local, sem alterar o comportamento de produção.
- Documentado o desenho de integração por baixa realizada: granularidade mínima
  auditável, matriz de lacunas do reader agregado e separação explícita entre
  projeção financeira e interpretação fiscal.
- Implementada a baixa canônica imutável no mesmo passe da projeção de posição,
  com quantidade solicitada/efetiva, receita, custo, taxas, moeda, identidade e
  eventos; reader por período e agregação por ticker compartilham essa fonte.

### Adicionado — motor canônico de eventos corporativos (31/07/2026)

- Criado motor puro e independente de provedor para splits, grupamentos, bonificações e subscrições, com uma única convenção de fator multiplicativo.
- A projeção preserva custo total, recalcula preço médio e mantém subscrições como direitos sem aumento automático de quantidade.
- A coleta global passou a normalizar `stockDividends` e `subscriptions` da BRAPI Pro e fatores explícitos de `Stock Splits` do Yahoo, com identidade determinística e payload auditável.
- O scheduler agora apenas cataloga eventos globais em savepoints por ativo; a aplicação legada que mutava posições e criava transações incompatíveis foi removida.
- Adicionadas regressões para idempotência, AERI3, bonificação, subscrição, split, grupamento e preservação de custo.

### Corrigido — dividendos históricos ajustados por eventos societários (31/07/2026)

- O adaptador complementar do Yahoo passou a desfazer, por evento, somente os fatores de split/grupamento explicitamente publicados após a Data Ex.
- A normalização preserva no payload auditável o valor apresentado pelo provedor e o fator acumulado aplicado, sem relaxar a reconciliação econômica estrita.
- Adicionada regressão para o caso real de AERI3: dividendo ajustado de `0.41404`, grupamento posterior `0.05` e valor histórico normalizado `0.020702`.
- A carga integral não foi repetida neste bloco corretivo; uma nova execução controlada continua sujeita ao gate operacional e ao SHA publicado.

### Alterado — documentação viva alinhada ao contrato canônico v2 (31/07/2026)

- README, ROADMAP e documentos gerais de arquitetura, dados canônicos e
  operação deixaram de apresentar o seed v1 e a materialização por carteira
  como estado atual.
- O fluxo documentado agora persiste somente eventos em `asset_dividends` e
  calcula direitos sob demanda; a contração física permanece explicitamente
  pendente da janela controlada da Issue #158.
- Regressão documental protege as fronteiras v2 e impede o retorno das
  afirmações operacionais obsoletas.
- O runbook mestre e os gates agregados #158/#216 foram sincronizados: a
  implementação v2 está concluída e somente duas execuções reais controladas e
  a contração física condicionada permanecem pendentes.

### Removido — modelos ORM das tabelas legadas de Proventos (31/07/2026)

- `Dividend` e `DividendsSyncJob` foram removidos do runtime e de
  `app.models.__init__`; `Base.metadata` não registra mais `dividends` nem
  `dividends_sync_jobs`.
- Testes que consultavam a tabela legada apenas para provar ausência de escrita
  passaram a validar diretamente os eventos globais em `asset_dividends`.
- A migration histórica de criação do sync job ficou autocontida e a migration
  de contração continua usando SQL físico, sem depender dos modelos removidos.

### Adicionado — contração física protegida do legado de Proventos (31/07/2026)

- A migration `20260731_drop_legacy_divs` foi preparada para remover
  `dividends` e `dividends_sync_jobs` somente depois de confirmar que ambas as
  tabelas estão vazias.
- A verificação ocorre para as duas tabelas antes do primeiro `DROP`, impedindo
  contração parcial quando ainda houver dados legados.
- O downgrade exige restauração do backup aprovado, pois recriar estruturas
  vazias não recuperaria dados descartados. A migration foi versionada e
  testada, mas não foi executada em nenhum banco neste bloco.

### Removido — inventário específico do modelo legado (31/07/2026)

- `proventos_model_audit_service.py`, sua CLI e o teste exclusivo foram
  removidos após o inventário genérico de pré-produção assumir a contagem física
  por reflexão e rollback.
- Regressão estrutural impede o retorno dos dois módulos e de seus imports.
- As políticas do inventário foram corrigidas: `asset_dividends` é o catálogo
  global; `dividends` contém direitos legados descartáveis e reconstruíveis.

### Removido — relacionamentos ORM de direitos materializados (31/07/2026)

- Foram removidos `Portfolio.dividends`, `AssetDividend.portfolio_dividends`,
  `Dividend.portfolio` e `Dividend.asset_dividend`, todos sem consumidores.
- O arquivo histórico `test_proventos_issue95.py`, baseado em linhas
  materializadas e já incompatível com a leitura canônica, foi substituído por
  cobertura estrutural da ausência dos relacionamentos.
- Os contratos ainda exclusivos de schema estrito e leitura sem mutação foram
  portados para a suíte canônica de direitos calculados sob demanda.

### Alterado — enums de Proventos independentes do ORM legado (31/07/2026)

- `DividendType` e `DividendStatus` foram movidos para
  `app.models.dividend_enums`, módulo puro sem SQLAlchemy.
- Modelo global, serviços, schemas e rotas passaram a importar os enums pelo
  módulo neutro; `dividend.py` apenas os reexporta para compatibilidade.
- Regressões estruturais impedem dependência ORM no novo módulo e novos imports
  dos enums a partir do arquivo legado.

### Removido — leitura de runtime de `dividends_sync_jobs` (31/07/2026)

- O seed pré-produção v2 não declara mais fronteira `inspect_only`, não consulta
  `DividendsSyncJob` e não expõe `sync_jobs` nas contagens do envelope.
- A auditoria física deixou de importar o modelo ou publicar
  `legacy_sync_job_rows`; permanecem apenas eventos canônicos e linhas legadas
