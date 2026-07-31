# Arquitetura canônica de Proventos

> Decisão arquitetural: 30/07/2026  
> Issue: #226  
> Estado: aprovada; migração incremental pendente

## Regra fundamental

Todo provento pertence exclusivamente a um ativo. A carteira não armazena uma
cópia do evento: ela consulta o catálogo global e calcula seu eventual direito
financeiro com base na posição histórica na data de direito.

## Modelo canônico

- `asset_dividends`: única fonte de verdade dos eventos globais.
- `assets`: identidade do ativo ao qual o evento pertence.
- `transactions`: histórico usado para reconstruir a posição elegível.
- `dividends`: legado reconstruível durante a transição; não é fonte canônica.
- Uma projeção por carteira somente poderá existir futuramente se medições
  demonstrarem necessidade. Nesse caso, deverá ser explicitamente derivada,
  versionada, invalidável e reconstruível.

## Fluxo alvo

1. Provedores publicam observações vinculadas ao ativo.
2. A reconciliação produz um evento econômico global em `asset_dividends`.
3. Endpoints e serviços de carteira consultam os eventos globais.
4. Um serviço canônico calcula a posição histórica na data de direito.
5. Proventos, Resumo, Patrimônio, Rentabilidade, snapshots e IRPF consomem o
   mesmo resultado derivado.

A carteira atual não define o histórico: um ativo já vendido pode continuar
gerando um direito histórico quando havia posição elegível. De modo equivalente,
possuir o ativo hoje não cria direito retroativo.

## Invariantes

- A identidade econômica não contém `portfolio_id`.
- A coleta não lê carteiras ou transações e não materializa direitos.
- Nenhum endpoint de carteira chama provedor externo.
- O mesmo evento global nunca é duplicado por carteira.
- Alterar uma transação histórica pode alterar o direito derivado, mas não o
  evento global.
- Eventos não monetários permanecem classificados no catálogo e não entram
  automaticamente em agregados de caixa.
- Ausência de posição elegível produz zero direito, não ausência do evento.
- Todos os consumidores financeiros usam uma única política para Data Com,
  Data Ex, pagamento, quantidade elegível, bruto, imposto e líquido.

## Migração incremental

### Bloco 1 — contrato e suspensão

- Formalizar este desenho.
- Marcar contrato e runbook v1 como suspensos.
- Proibir nova execução operacional.

### Bloco 2 — inventário de consumidores e portas de escrita

- Enumerar todas as leituras e escritas em `dividends`.
- Classificar cada consumidor por Proventos, Resumo, Patrimônio,
  Rentabilidade, snapshots, IRPF e APIs.
- Desativar rotas e integrações legadas incompatíveis sem remover dados.
- `POST /api/v1/sync/proventos/{portfolio_id}` e a integração
  `brapi_dividends.py` foram removidos por violarem a separação entre coleta
  global e consulta de carteira.

#### Portas de escrita restantes

| Porta | Responsabilidade atual | Classificação | Destino |
|---|---|---|---|
| `POST/DELETE /portfolios/{id}/dividends` | CRUD manual diretamente em `dividends` | Removido | Escrita pública desativada; ajuste manual futuro deve atuar no evento canônico |
| `POST /portfolios/{id}/dividends/sync` | Disparava sincronização/materialização por carteira | Removido | Rota desativada e protegida por regressão de contrato |
| `GET /portfolios/{id}/dividends` e `dividend_service.py` | Projeção de direitos por carteira | Canônico | Read-only sobre `asset_dividends`, `assets` e `transactions`, sem acesso à tabela legada |
| `proventos_daily_sync_service.py` | Coleta eventos globais e invalida consumidores | Canônico | Materialização e campo de resultado legado retirados |
| `dividend_backfill_service.py` | Coleta global de eventos | Canônico | O materializador legado foi removido; o módulo grava somente `asset_dividends`, sem `portfolio_id`, `Transaction` ou `Dividend` |
| `asset_market_pipeline_service.py` | Coleta eventos globais por ativo | Canônico | Materialização, argumento e resultado legados retirados |
| `asset_seed_service.py` e `asset_onboarding_service.py` | Chamam o pipeline sem solicitar materialização | Canônico | Argumento e métricas legadas removidos dos callers de aplicação |
| Batch e CLIs de mercado | Coletam eventos globais sem opção de materialização | Canônico | Interface contraída e protegida por regressão |
| `run_proventos_sync.py` | Coleta manual global, inclusive por ticker | Canônico | Materialização final removida; não grava direitos por carteira |
| `dividend_history_seed_service.py` | Complemento histórico global via Yahoo | Canônico | Materialização retirada; persiste exclusivamente `asset_dividends` |
| `full_market_rebuild_service.py` | Orquestra a sincronização global de Proventos | Canônico | Resume ativos varridos, sincronizados e falhos; não importa, chama ou contabiliza materialização |
| `dividend_entitlement_service.py` | Helpers legados de quantidade e valor líquido | Removido | O módulo ficou sem callers após a retirada dos materializadores; regressão estrutural impede sua reintrodução |
| `portfolio_service.py` | Totais e agrupamentos de Proventos no resumo/posições legados | Canônico | Assinaturas preservadas; agregações read-only usam direitos elegíveis, pagos, líquidos e em BRL |
| Exclusão de carteira | `portfolio_delete_service.delete_portfolio_safely` | Ativo | A implementação órfã em `portfolio_service.py` foi removida; a porta ativa ainda exclui dependências legadas de forma explícita |
| Seed pré-produção | Catálogo global canônico | Canônico | Contrato `pre-prod-dividends-seed.v2`; lê `assets`/`asset_dividends`, escreve somente `asset_dividends` e não contém superfície de materialização |
| `scheduler.py` legado e scheduler diário ativo | Atualização do catálogo global | Canônico | Scheduler diário preservado; job FII quebrado e redundante removido do legado; o seed de ativos já enriquece tickers elegíveis com eventos globais |
| `proventos_legacy_link_service.py` e sua CLI | Dry-run de vínculos de direitos materializados | Removido | A evidência histórica já registrava zero direitos sem vínculo; o cálculo sob demanda tornou o backfill incompatível com a arquitetura alvo |
| `proventos_model_audit_service.py` e sua CLI | Inventário específico do legado | Removido | Substituído pelo inventário genérico read-only, baseado em reflexão e rollback; nenhum serviço de runtime importa `Dividend` para auditoria |
| `dividend_enums.py` | Tipos e status públicos de Proventos | Canônico | Não importa SQLAlchemy nem o ORM `Dividend`; serviços, schemas, rotas e o catálogo global dependem somente deste módulo neutro |
| Relacionamentos ORM de `Dividend` | Navegação e cascata por `Portfolio`/`AssetDividend` | Removido | Zero consumidores; exclusão física continua governada por FKs e pelo serviço explícito de remoção de carteira |

Nenhuma dessas portas pode ser removida isoladamente antes de seu consumidor ou
substituto estar coberto. Durante a migração, é proibido reintroduzir
`materialize_asset_dividends`, acoplar coleta global a carteiras ou adicionar
reconciliação ou CRUD de `Dividend`.

#### Consumidores de leitura

| Domínio | Serviços principais | Dependência legada | Ordem |
|---|---|---|---|
| API/Frontend Proventos | `proventos_service.py`, `dividend_service.py`, router `dividends.py` | Lista, totais, série mensal e detalhes usam `Dividend` | Primeiro consumidor do serviço canônico |
| Resumo e Patrimônio | `portfolio_summary_service.py`, `canonical_positions_service.py`, `canonical_dividend_aggregation_service.py` | Direitos canônicos read-only | Migrado após a API |
| Rentabilidade | `rentabilidade_service.py` | Fluxos recebidos alimentam retorno | Migrar com política única de caixa líquido |
| Snapshots/TWR | `portfolio_snapshot_canonical_twr_service.py`, `portfolio_class_snapshot_service.py` | Ordenam e aplicam direitos persistidos | Migrar antes de reconstruir snapshots |
| IRPF | `irpf_service.py` | Cruza `Dividend` com `AssetDividend` | Migrar após bruto, imposto e líquido canônicos |
| Metas | `goals_service.py` | Soma janela de 12 meses | Migrar depois do agregador canônico |
| Auditoria pré-produção | inspeções, comparador e auditoria do modelo v1 | Conta materializações e divergências | Congelar como v1; substituir no novo contrato |

O modelo e as migrations históricas permanecem intocados neste bloco. Testes que
instanciam `Dividend` continuam válidos como caracterização do legado, mas não
definem a arquitetura alvo.

#### Ordem obrigatória de migração

1. Criar o serviço puro de direito por evento e posição histórica.
2. Migrar a API de Proventos e provar paridade/explicar diferenças.
3. Migrar Resumo, Patrimônio e o agregador compartilhado.
4. Migrar Rentabilidade, snapshots/TWR, IRPF e Metas.
5. Retirar materialização dos pipelines, schedulers e mutações.
6. Desativar CRUD/sync por carteira e provar zero referências de escrita.
7. Contrair modelo, relações, testes legados e schema em migration própria.

### Bloco 3 — serviço canônico de direitos

- Implementado o núcleo puro `canonical_dividend_entitlement.py`, sem acesso a
  banco, endpoints ou efeitos colaterais.
- `record_date` confiável é a única data aceita para calcular a posição. Evento
  sem Data Com permanece ambíguo e não usa Data Ex como fallback.
- Dividendos, JCP, rendimentos e amortizações são monetários; bonificações,
  subscrições e `OUTROS` não entram automaticamente em agregados de caixa.
- O resultado explicita quantidade elegível, bruto, retenção, líquido, moeda e
  motivo da elegibilidade ou exclusão.
- As regressões cobrem ausência de posição, venda posterior, recompra, compra na
  Data Ex sem Data Com, JCP e histórico inválido.

Este núcleo ainda não está conectado a endpoints ou consultas ORM. Essa
integração será feita consumidor por consumidor, começando pela API de
Proventos, depois de um adaptador read-only carregar eventos e movimentos.

O adaptador read-only `canonical_dividend_entitlement_reader.py` já conecta
`asset_dividends` e `assets` ao histórico completo de `transactions`, usando
o par `(ticker, asset_type)` enquanto as transações não possuem `asset_id`.
Ele não consulta `dividends`, não grava projeções e não altera endpoints. A
moeda vem explicitamente do ativo; cadastro sem moeda é rejeitado.


### Bloco 4 — migração de consumidores

- Migrar um consumidor por commit pequeno.
- Comparar resultados legados e canônicos com fixtures e PostgreSQL.
- Não alterar o schema destrutivamente.

#### API de Proventos

A leitura pública de Proventos foi migrada para o adaptador canônico:

- `summary`, listagem, histórico mensal e distribuição consultam somente
  `asset_dividends`, `assets` e `transactions`;
- o contrato HTTP e seus schemas permanecem inalterados;
- `id` na listagem identifica o evento global em `asset_dividends`;
- quantidade, bruto, retenção e líquido são derivados da posição histórica;
- `RECEBIDO` e `A_RECEBER` são derivados de `payment_date` em relação à data
  corrente, sem depender do status materializado;
- evento monetário sem `record_date` não aparece como direito da carteira;
- bonificação e subscrição continuam visíveis como eventos não monetários,
  sem contaminar totais financeiros;
- filtros, paginação, histórico e distribuição operam sobre o mesmo conjunto
  canônico, sem leitura ou escrita em `dividends`.

Diferenças em relação ao legado são deliberadas: não há fallback de Data Ex
para elegibilidade, o status não pode ficar obsoleto e valores materializados
divergentes são substituídos pelo cálculo reproduzível. A tabela `dividends`
permanece intacta para os consumidores ainda não migrados.

#### Resumo e Patrimônio

Os KPIs do Resumo e os grupos de Patrimônio foram migrados para
`canonical_dividend_aggregation_service.py`:

- o agregador carrega os direitos canônicos uma vez por projeção;
- somente direitos elegíveis e já pagos entram nos totais;
- janelas usam `payment_date`, inclusive o acumulado de 12 meses;
- Patrimônio limita o agrupamento aos tickers das posições abertas, enquanto
  Resumo preserva todo o histórico elegível da carteira;
- eventos não BRL ficam fora destes KPIs até existir política canônica de
  conversão cambial, evitando somar moedas diferentes;
- O agregador legado `dividend_aggregation_service.py` foi removido após
  Rentabilidade, snapshots e os demais consumidores migrarem para o agregador
  canônico.

Os contratos HTTP e schemas não mudaram. A tabela `dividends` permanece intacta
somente para as portas de escrita, auditoria e inspeção ainda não contraídas.

#### Rentabilidade

Os KPIs de Rentabilidade passaram a carregar os proventos recebidos pelo
agregador canônico:

- total histórico e janela de 12 meses são obtidos em uma única carga;
- somente direitos elegíveis, monetários em BRL e pagos até a data de cálculo
  entram nos KPIs;
- a janela de 12 meses usa `payment_date` e o valor líquido do direito;
- falha do leitor preserva o comportamento seguro anterior, retornando zero e
  registrando aviso, sem consultar `dividends`.

A tabela legada continua disponível exclusivamente para portas de escrita,
auditoria e inspeção ainda não contraídas; não há agregador legado compartilhado
entre consumidores.

#### Snapshots e TWR

Os rebuilds consolidado, canônico e por classe passaram a carregar direitos
diretamente de `asset_dividends` e do histórico de `transactions`:

- somente direitos elegíveis, monetários em BRL e com pagamento conhecido
  participam do fluxo de caixa;
- pagamentos em dias não úteis são reconhecidos no primeiro fechamento útil
  subsequente;
- o acumulado e o valor diário usam a mesma projeção temporal;
- o gate automático de manutenção compara o snapshot com a mesma fonte
  canônica, evitando reconstruções cíclicas;
- `dividends` permanece intacta para consumidores ainda não migrados, mas não
  participa mais de snapshots ou TWR.

Contratos HTTP, schema, dados persistidos e entradas operacionais não foram
alterados. As execuções de Proventos permanecem suspensas.

#### IRPF e Metas

Os rendimentos do relatório de IRPF e a renda mensal das metas de Proventos
passaram a usar os direitos canônicos:

- IRPF considera apenas direitos elegíveis, monetários em BRL e pagos dentro do
  ano-calendário;
- dividendos e rendimentos usam o valor líquido canônico, enquanto JCP preserva
  separadamente bruto, retenção e líquido calculados pelo núcleo;
- Metas calcula a média mensal sobre o valor líquido pago nos últimos 12 meses,
  sem fallback para eventos futuros, ambíguos ou em outra moeda;
- nenhum dos dois consumidores consulta ou grava `dividends`.

As referências restantes à tabela legada pertencem a portas de escrita/CRUD,
auditoria, inspeção e helpers de compatibilidade. A contração desses caminhos
será feita em blocos separados.

### Bloco 5 — contração do legado

- Confirmar zero consumidores e zero portas de escrita.
- Preservar/exportar evidência necessária.
- Remover `dividends` somente por migration separada e reversível.
- Atualizar contratos, documentação e Issues relacionadas.

### Bloco 6 — novo seed isolado

- Publicar novo contrato com escrita exclusiva em `asset_dividends`.
- Adquirir advisory lock antes de inspeção e rede.
- Separar gates de host, identidade da imagem e testes internos do container.
- Executar dry-run read-only antes de nova autorização.
- Provar duas execuções idempotentes somente após todos os gates.

## Critério de conclusão

A migração estará concluída quando:

- `asset_dividends` for a única fonte persistida dos eventos;
- nenhuma porta ativa gravar direitos por carteira;
- todos os consumidores usarem o cálculo derivado canônico;
- resultados financeiros tiverem paridade explicada e testada;
- `dividends` puder ser removida sem perda de informação canônica;
- um novo contrato operacional substituir formalmente a versão v1 suspensa.

Até lá, nenhuma execução do wrapper
`Invoke-PreProdDividendsIdempotency.ps1` está autorizada.
