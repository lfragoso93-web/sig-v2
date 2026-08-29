# Fluxo canônico de bootstrap e carga de dados — SGI v2

> Documento arquitetural canônico para reconstrução inicial, sincronização incremental e rebuild de dados globais. Qualquer seed, backfill, rebuild ou Central de Bootstrap deve respeitar este fluxo.

## Objetivo

Evitar que estágios de carga sejam executados fora de ordem, sobrescrevam dados certificados ou misturem fontes com responsabilidades diferentes.

Este documento distingue três operações que não são equivalentes:

1. **Initial Bootstrap** — construção de uma base vazia ou recém-reconstruída;
2. **Incremental Sync** — atualização rotineira de dados já persistidos;
3. **Full Market Rebuild** — reconstrução de derivados/cobertura sobre uma base global já preparada.

`full_market_rebuild` **não substitui** o Initial Bootstrap.

## Princípios

- runtime financeiro é DB-first;
- providers participam apenas de bootstrap, ingestão, sincronização ou reconciliação explícitas;
- dados globais devem estar persistidos e certificados antes da importação de carteiras reais;
- dados de carteira nunca devem ser usados como mecanismo para descobrir ou criar silenciosamente dados globais;
- cada domínio possui uma fonte canônica e, quando necessário, fallbacks explicitamente limitados;
- operações globais idempotentes devem preferir `insert-if-missing`/upsert conservador e nunca substituir silenciosamente uma fonte de maior autoridade por outra de menor autoridade;
- `ready_for_real_data=true` somente após todos os estágios obrigatórios estarem certificados.

## 1. Universo B3 — autoridade e precedência de fontes

### Decisão alvo

Para ativos negociados na B3 (`ACAO`, `FII`, `ETF_NACIONAL`, `BDR`):

1. **B3 COTAHIST é a fonte oficial de baseline histórico da B3**;
2. o COTAHIST deve ser evoluído para fornecer também o máximo possível de identidade/metadados oficiais disponíveis no layout histórico;
3. **BRAPI é fonte de enriquecimento e atualização**, especialmente para campos não fornecidos ou não normalizados pelo COTAHIST, como nome amigável, setor, logo, cobertura e dados recentes de provider;
4. BRAPI não deve apagar nem substituir silenciosamente fatos históricos oficiais já persistidos a partir do COTAHIST;
5. Yahoo não é fonte primária do universo B3.

### Estado atual do código

O parser `app.integrations.b3_cotahist` já possui DTO tipado mínimo com
identidade, classificação, OHLCV, fator de cotação e ISIN usando `Decimal`.

O estágio B3 de pré-produção já possui caminho COTAHIST-first para:

- classificar registros B3 suportados sem chamadas externas;
- criar/upsertar catálogo mínimo em `assets`;
- persistir histórico oficial de preços com `open`, `high`, `low`, `close`,
  `volume` e `source=b3_cotahist`;
- preferir mercado à vista (`010`) sobre fracionário (`020`) na mesma data.

BRAPI permanece como fonte de enriquecimento/atualização posterior para campos
complementares, não como pré-requisito para o catálogo B3 existir. O seed BRAPI
não cria novos ativos B3 quando o COTAHIST não os descobriu; ele apenas preenche
lacunas de metadados em ativos B3 já persistidos. Catálogos de domínios onde a
BRAPI é canônica, como CRIPTO suportado, continuam pertencendo ao estágio
dedicado desse domínio.

### Evolução necessária

Evolução remanescente em blocos pequenos:

1. auditar precedência para impedir downgrade de autoridade em rotas futuras;
2. refletir a nova ordem na Central de Bootstrap quando a #253 for retomada.

## 2. Ordem canônica do Initial Bootstrap

### Fase 0 — Schema e infraestrutura

- migrations/Alembic no head aprovado;
- PostgreSQL/Redis/serviços saudáveis;
- identidade operacional por branch/SHA/run_id quando aplicável;
- nenhum dado real importado ainda.

### Fase 1 — Catálogos globais

#### 1A. Universo B3

**Alvo arquitetural:** COTAHIST-first.

- descobrir/criar ativos B3 a partir do layout oficial possível;
- persistir identidade/metadados oficiais disponíveis;
- posteriormente enriquecer via BRAPI.

**Estado atual:** o estágio B3 já pode criar catálogo mínimo via COTAHIST antes
do histórico. BRAPI deve atuar depois como enriquecimento.

#### 1B. Cripto

- universo suportado canônico definido pela integração BRAPI/contrato vigente;
- persistir apenas ativos suportados pelo SGI.

#### 1C. Tesouro Direto

- catálogo oficial do Tesouro;
- nenhuma BRAPI deve substituir o catálogo oficial.

#### 1D. Outros catálogos

- cada classe usa sua fonte oficial/canônica própria;
- nenhum catálogo deve depender de carteira de usuário.

### Fase 2 — Históricos globais de preços

#### B3

- fonte histórica oficial: **B3 COTAHIST**;
- persistência em `asset_prices`;
- identidade por ativo + timestamp;
- COTAHIST prevalece sobre históricos genéricos para o baseline B3.

#### Tesouro

- fonte oficial dedicada;
- histórico e último preço separados conforme contrato Tesouro.

#### Cripto e outras classes

- provider dedicado por capacidade;
- backfill genérico só atua onde não existe provider/bootstrap dedicado.

### Fase 3 — Séries auxiliares globais

- benchmarks e taxas macroeconômicas;
- câmbio;
- demais séries globais obrigatórias.

Cada série deve preservar sua fonte canônica própria; fallback nunca substitui automaticamente uma fonte oficial estável.

### Fase 4 — Proventos globais

Tabela canônica: `asset_dividends`.

Política alvo de provider:

1. **BRAPI authoritative** para Proventos quando houver cobertura válida;
2. Yahoo apenas **fallback de cobertura**, nunca fonte concorrente para o mesmo evento já coberto pela BRAPI;
3. valores monetários normalizados pelo SGI antes da identidade/persistência;
4. precisão máxima canônica de `value_per_unit` e `gross_value_per_unit`: **8 casas decimais**, compatível com `Numeric(18, 8)`;
5. nenhuma materialização de direitos por carteira.

### Fase 5 — Eventos corporativos globais

Tabela canônica: `corporate_events`.

- eventos pertencem ao ativo, não à carteira;
- splits, bônus, subscrições, ticker changes e demais eventos usam o contrato global vigente;
- transações históricas não são mutadas para “aplicar” evento corporativo;
- precedência de provider deve ser explicitamente documentada no domínio.

### Fase 6 — Auditoria global de cobertura

Só após catálogos, preços, séries auxiliares, Proventos e eventos corporativos:

- cobertura temporal;
- lacunas;
- duplicidades;
- órfãos;
- fontes observadas;
- lifecycle dos ativos;
- erros e bloqueios por domínio.

Essa fase não cria dados de carteira.

### Fase 7 — Importação de dados de carteira

Somente depois da certificação global:

- usuários/carteiras reais;
- CSV/transações reais;
- aliases/tickers devem ser resolvidos antes de criar ativos.

Importação de carteira não pode descobrir silenciosamente provider nem substituir o catálogo global.

### Fase 8 — Derivados de carteira

- posições;
- preço médio/custo;
- direitos de Proventos calculados sob demanda;
- efeitos de eventos corporativos conforme motor canônico;
- nenhuma duplicação de fatos globais em tabelas de carteira.

### Fase 9 — Snapshots, valuation e TWR

Executar somente após:

- preços globais certificados;
- transações importadas;
- posições reconciliadas;
- séries auxiliares disponíveis.

### Fase 10 — Reconciliação final e readiness

Validar:

- patrimônio;
- rentabilidade;
- Proventos;
- Tesouro;
- Renda Fixa;
- IRPF quando aplicável;
- restart/persistência/idempotência;
- ausência de dependência de provider em GETs/cálculos financeiros.

Somente então considerar `ready_for_real_data=true`.

## 3. Sincronização incremental

A sincronização incremental atualiza uma base já inicializada e **não deve repetir indiscriminadamente o Initial Bootstrap**.

Regras:

- COTAHIST pode complementar anos/períodos ausentes sem substituir identidades já persistidas;
- BRAPI atualiza/enriquece catálogo e dados recentes dentro de sua responsabilidade;
- backfills operam apenas em gaps comprovados;
- providers dedicados prevalecem sobre backfill genérico;
- Proventos BRAPI-first; Yahoo somente fallback de cobertura;
- eventos corporativos seguem provider canônico do domínio;
- qualquer fallback utilizado deve ficar observável na coluna/source/evidência correspondente.

## 4. Full Market Rebuild

`full_market_rebuild` é uma operação de manutenção/reconstrução sobre uma base global já preparada.

Ele pode executar, conforme contrato vigente:

- backfill/auditoria de preços globais;
- Tesouro;
- benchmarks;
- snapshots/TWR;
- manutenção;
- auditoria final de cobertura.

Ele **não deve** ser usado para:

- bootstrap de uma base vazia;
- criar silenciosamente todos os catálogos;
- contornar gates de Proventos/eventos;
- importar CSV real;
- substituir a ordem de reconstrução da #158.

## 5. Matriz de autoridade por domínio

| Domínio | Fonte primária/canônica | Fonte complementar/fallback | Escrita principal | Pré-requisito |
| --- | --- | --- | --- | --- |
| Catálogo B3 | B3 COTAHIST (alvo) | BRAPI para enriquecimento | `assets` | schema |
| Histórico B3 | B3 COTAHIST | nenhuma fonte genérica deve sobrescrever | `asset_prices` | catálogo B3 |
| Cripto | contrato BRAPI/universo suportado | conforme capability explícita | `assets`, preços dedicados | schema |
| Tesouro catálogo | fonte oficial | nenhuma substituição por BRAPI | catálogo/`assets` | schema |
| Tesouro histórico | fonte oficial | conforme contrato Tesouro | preços Tesouro | catálogo Tesouro |
| Benchmarks | fontes oficiais | fallback explicitamente governado | séries/taxas | schema |
| Câmbio | fonte canônica vigente | fallback explicitamente governado | série FX | schema |
| Proventos | BRAPI | Yahoo somente fallback de cobertura | `asset_dividends` | catálogo |
| Eventos corporativos | provider canônico do domínio | fallback explícito | `corporate_events` | catálogo |
| Cobertura | dados já persistidos | — | evidência/status | todos globais |
| Transações | arquivo/entrada do usuário | resolução por catálogo | `transactions` | globais certificados |
| Posições | cálculo interno | — | derivados | transações |
| Snapshots/TWR | cálculo interno | — | snapshots | posições + mercado |

## 6. Política de precisão para Proventos

`asset_dividends.value_per_unit` e `gross_value_per_unit` usam `Numeric(18, 8)`.

Contrato alvo:

- usar `Decimal`;
- máximo de 8 casas decimais;
- normalização centralizada com quantum `0.00000001`;
- arredondamento único e documentado pelo domínio;
- identidade e comparação devem usar o valor já normalizado;
- diferenças entre providers não justificam competição quando a fonte primária possui cobertura válida.

## 7. Gates operacionais

Antes de cada estágio real:

- confirmar Issue relacionada;
- confirmar branch `stable-15jun` e SHA remoto/local;
- confirmar working tree limpa;
- confirmar dependências anteriores concluídas;
- registrar `run_id`/evidência quando o contrato exigir;
- executar somente as tabelas autorizadas para aquele estágio;
- comparar estado antes/depois;
- interromper ao primeiro blocker não reconciliado.

## 8. Relação com Issues

- #158 — reconstrução limpa e ordem operacional real;
- #216 — gate agregado de seeds isolados;
- #226 — Proventos;
- #253 — futura Central de Bootstrap deve refletir este contrato;
- #227 — gate-mãe antes de dados reais;
- #129 — eventos corporativos;
- #130 — evolução BRAPI/cobertura/enriquecimento;
- #272 — dívida física de `corporate_events`.

## 9. Estado de implementação desta decisão

Este documento descreve o **contrato alvo**.

Já implementado:

- COTAHIST como fonte histórica B3 de `asset_prices`;
- BRAPI como catálogo B3 transitório;
- providers dedicados excluídos do backfill genérico;
- Tesouro oficial;
- benchmarks/câmbio isolados;
- Proventos globais em `asset_dividends`;
- eventos corporativos globais;
- separação DB-first/provider-boundary.

Ainda a implementar antes de considerar o fluxo plenamente convergido:

1. evoluir COTAHIST para catálogo/baseline B3 first-class;
2. inverter o estágio B3 de BRAPI-first para COTAHIST-first;
3. limitar BRAPI a enriquecimento/atualização quando COTAHIST já definiu o fato oficial;
4. simplificar Proventos para BRAPI authoritative + Yahoo fallback-only;
5. centralizar a normalização de Proventos em 8 casas;
6. fazer `system-bootstrap`/Central de Bootstrap refletirem explicitamente esta ordem e dependências.
