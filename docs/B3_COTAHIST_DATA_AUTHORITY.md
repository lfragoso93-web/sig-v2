# Autoridade de dados B3 COTAHIST — SGI v2

> Inventário arquitetural do arquivo oficial B3 COTAHIST e sua relação com o schema canônico do SGI v2. Este documento define quais fatos devem ser tratados como oficiais, quais são apenas candidatos a enriquecimento e quais ainda exigem evolução de schema antes de serem persistidos.

## Objetivo

Transformar o COTAHIST de uma fonte usada apenas para fechamento histórico em uma fonte B3 first-class para baseline oficial de ativos e preços, reduzindo dependência de providers agregadores durante o bootstrap inicial.

Este documento complementa `docs/BOOTSTRAP_DATA_FLOW.md`.

## Fonte oficial

Layout oficial B3: `SeriesHistoricas_Layout.pdf`, registro `01 - Cotações históricas por papel-mercado`, revisão 2.0 de 05/10/2020.

O registro diário possui 245 bytes e contém identidade do papel, classificação de mercado, preços, liquidez, ISIN e informações auxiliares.

## Estado atual do SGI

`app.integrations.b3_cotahist` já extrai o DTO mínimo necessário para a fase B3:

- `CODNEG` / ticker;
- data do pregão;
- `TPMERC` / mercado;
- `NOMRES` / nome resumido;
- `ESPECI` / especificação;
- `MODREF` / moeda;
- `PREABE`, `PREMAX`, `PREMIN`, `PREULT` / OHLC;
- `VOLTOT` / volume financeiro;
- `FATCOT` / fator de cotação;
- `CODISI` / ISIN.

O estágio B3 de pré-produção já usa o COTAHIST para criar/upsertar catálogo
mínimo antes do histórico. `rebuild_b3_historical_market` persiste OHLCV oficial
em `asset_prices` e preserva a regra de precedência de mercado à vista sobre
fracionário.

O schema atual já possui espaço para parte importante do que o COTAHIST oferece:

### `assets`

- `ticker`;
- `name`;
- `asset_type`;
- `currency`;
- `last_price`;
- `sector` / `sub_sector`;
- `isin_code`;
- campos de provider/enriquecimento.

### `asset_prices`

- `timestamp`;
- `open`;
- `high`;
- `low`;
- `close`;
- `volume`;
- `source`.

O modelo `asset_prices` ainda não possui colunas próprias para preço médio, melhores ofertas, número de negócios e quantidade negociada.

## Matriz do registro 01

| Campo B3 | Posições | Significado | Uso SGI alvo | Autoridade proposta | Persistência atual |
| --- | ---: | --- | --- | --- | --- |
| `TIPREG` | 1-2 | Tipo do registro | validação do parser | B3 | não persistir |
| `DTPREGAO` | 3-10 | Data do pregão | timestamp do preço | B3 | `asset_prices.timestamp` |
| `CODBDI` | 11-12 | Classificação BDI | classificação/filtro do instrumento | B3 | não existe coluna dedicada |
| `CODNEG` | 13-24 | Código de negociação | ticker canônico observado | B3 | `assets.ticker` |
| `TPMERC` | 25-27 | Tipo de mercado | distinguir vista/fracionário/outros | B3 | parser usa, não persiste |
| `NOMRES` | 28-39 | Nome resumido do emissor | nome oficial resumido de baseline | B3 | candidato a `assets.name` |
| `ESPECI` | 40-49 | Especificação do papel | classificar ON/PN/BDR/fundo/direitos e estados ex | B3 | não existe coluna dedicada |
| `PRAZOT` | 50-52 | Prazo do mercado a termo | fora do universo spot principal | B3 | não persistir no bootstrap spot |
| `MODREF` | 53-56 | Moeda de referência | moeda observada | B3 | candidato a `assets.currency` |
| `PREABE` | 57-69 | Preço de abertura | OHLC oficial | B3 | `asset_prices.open` |
| `PREMAX` | 70-82 | Preço máximo | OHLC oficial | B3 | `asset_prices.high` |
| `PREMIN` | 83-95 | Preço mínimo | OHLC oficial | B3 | `asset_prices.low` |
| `PREMED` | 96-108 | Preço médio | dado histórico oficial opcional | B3 | sem coluna dedicada |
| `PREULT` | 109-121 | Último negócio | fechamento oficial | B3 | `asset_prices.close` |
| `PREOFC` | 122-134 | Melhor oferta de compra | microestrutura histórica opcional | B3 | sem coluna dedicada |
| `PREOFV` | 135-147 | Melhor oferta de venda | microestrutura histórica opcional | B3 | sem coluna dedicada |
| `TOTNEG` | 148-152 | Número de negócios | liquidez histórica | B3 | sem coluna dedicada |
| `QUATOT` | 153-170 | Quantidade negociada | liquidez histórica | B3 | sem coluna dedicada |
| `VOLTOT` | 171-188 | Volume financeiro | volume oficial | B3 | `asset_prices.volume` |
| `PREEXE` | 189-201 | Preço de exercício/contrato | opções/termo | B3 | fora do bootstrap spot atual |
| `INDOPC` | 202 | Indicador de correção | opções/termo | B3 | fora do bootstrap spot atual |
| `DATVEN` | 203-210 | Data de vencimento | derivativos/termo | B3 | fora do bootstrap spot atual |
| `FATCOT` | 211-217 | Fator de cotação | normalização correta de preços/lotes | B3 | não persistido hoje |
| `PTOEXE` | 218-230 | Exercício em pontos | derivativos | B3 | fora do bootstrap spot atual |
| `CODISI` | 231-242 | Código ISIN | identidade forte do papel | B3 | `assets.isin_code` |
| `DISMES` | 243-245 | Nº de distribuição | distinguir estados/emissões históricas | B3 | sem coluna dedicada |

## Decisão de autoridade

### 1. Fatos oficiais que o COTAHIST deve dominar

Para o baseline B3 histórico:

- ticker observado (`CODNEG`);
- data de negociação (`DTPREGAO`);
- mercado (`TPMERC`);
- classificação BDI (`CODBDI`);
- especificação do papel (`ESPECI`);
- ISIN (`CODISI`) quando presente;
- moeda (`MODREF`);
- fator de cotação (`FATCOT`);
- OHLC (`PREABE`, `PREMAX`, `PREMIN`, `PREULT`);
- volume financeiro (`VOLTOT`);
- número de negócios (`TOTNEG`) e quantidade (`QUATOT`) se o schema passar a suportá-los.

Esses fatos não devem ser sobrescritos silenciosamente por BRAPI/Yahoo quando já derivados do registro oficial para a mesma identidade temporal.

### 2. Campos que a BRAPI pode enriquecer

BRAPI permanece adequada para dados que o COTAHIST não modela ou não modela com riqueza suficiente, por exemplo:

- nome amigável/long name;
- setor e subsetor;
- logo;
- cobertura do provider;
- metadados atuais adicionais;
- informação recente quando ainda não existe arquivo COTAHIST oficial correspondente.

Regra: enriquecimento preenche lacunas ou atualiza campos cuja autoridade foi atribuída à BRAPI; não faz downgrade de fatos oficiais B3.

### 3. Yahoo

Yahoo não participa do catálogo nem do histórico oficial B3 quando existe cobertura COTAHIST.

Seu uso, quando existir em outro domínio, deve ser explicitamente fallback e observável.

## Classificação de ativos a partir do COTAHIST

`ESPECI`, `CODBDI`, `TPMERC` e o padrão de `CODNEG` oferecem sinais oficiais suficientes para construir uma classificação inicial, mas o mapeamento para `AssetType` deve ser explícito e testado.

Direção inicial:

- `BDR` -> `BDR`;
- especificações ON/PN/classes -> `ACAO`;
- fundos identificados pelo código BDI/especificação -> `FII` ou `ETF_NACIONAL` apenas quando a regra puder diferenciá-los com segurança;
- direitos, recibos, opções, termo, futuros e demais instrumentos fora do universo suportado devem ser classificados como inelegíveis, não convertidos silenciosamente em ativos spot.

Não inferir `FII` versus `ETF_NACIONAL` apenas pelo sufixo `11`; usar classificação oficial e, quando insuficiente, enriquecimento posterior.

## Mercado padrão versus fracionário

O parser atual aceita `TPMERC=010` (vista) e `020` (fracionário) e, para a mesma data/ticker, dá precedência ao mercado à vista.

Essa regra deve ser preservada para o histórico canônico de preços:

1. mercado à vista (`010`) é preferido;
2. fracionário (`020`) só cobre a data quando não houver registro à vista equivalente;
3. nunca persistir duas cotações diárias distintas para a mesma identidade `asset_id + timestamp` por causa de vista/fracionário.

## Precisão

Os preços do COTAHIST são publicados com duas casas implícitas no arquivo. O SGI persiste preços como `Numeric(18, 8)`.

Contrato:

- parsear o inteiro do layout usando `Decimal`, nunca `float` como representação intermediária canônica;
- converter os centavos oficiais para `Decimal`;
- persistir em `Numeric(18, 8)` sem inventar precisão adicional;
- não usar `round(float, 8)` como normalização canônica futura.

Essa mudança deve ocorrer no mesmo bloco funcional que introduzir o DTO COTAHIST tipado.

## Lacunas de schema identificadas

Antes de adicionar colunas, avaliar utilidade real para produto/analytics. O arquivo contém dados que hoje não cabem diretamente em `asset_prices`:

- `PREMED`;
- `PREOFC`;
- `PREOFV`;
- `TOTNEG`;
- `QUATOT`;
- `CODBDI`/`TPMERC`/`ESPECI`/`FATCOT` como metadados históricos.

Não criar migration apenas porque o campo existe na B3. Cada persistência nova deve ter consumidor ou requisito arquitetural explícito.

## Ordem alvo do estágio B3

### Initial Bootstrap

1. baixar/processar COTAHIST na janela aprovada;
2. construir catálogo B3 mínimo a partir das identidades oficiais observadas;
3. persistir histórico oficial de preços no mesmo domínio B3;
4. reconciliar duplicidades/mercado à vista versus fracionário;
5. enriquecer ativos via BRAPI sem substituir fatos oficiais;
6. auditar cobertura e lifecycle.

### Incremental Sync

1. completar COTAHIST oficial disponível ainda ausente;
2. usar BRAPI para metadados atuais e atualização recente dentro de sua responsabilidade;
3. quando um período oficial COTAHIST posteriormente se tornar disponível, ele prevalece sobre dados históricos de provider de menor autoridade para aquela data, mediante reconciliação explícita e auditável.

## Regras de sobrescrita

- `assets.ticker`: identidade oficial observada; mudança/alias exige contrato de ticker change, não overwrite cego;
- `assets.isin_code`: COTAHIST/B3 tem precedência quando presente e válido;
- `assets.name`: nome B3 pode criar baseline; BRAPI pode enriquecer para nome amigável conforme política de campo;
- `assets.currency`: B3 define baseline do instrumento nacional; provider não deve mudar silenciosamente;
- `asset_prices` histórico coberto pelo COTAHIST: B3 prevalece;
- `last_price`: cache derivado do histórico/preço recente canônico, nunca autoridade própria.

## Evolução recomendada em microblocos

1. **DTO/parser tipado COTAHIST** — concluído;
2. **classificador B3** — concluído para casos seguros, com `UNRESOLVED` para ambiguidade;
3. **catálogo COTAHIST-first** — concluído em upsert conservador de `assets`;
4. **OHLCV oficial** — concluído para `open/high/low/close/volume` com idempotência;
5. **BRAPI enrichment policy** — limitar atualizações por autoridade de campo;
6. **bootstrap/system bootstrap** — refletir a nova ordem e dependências;
7. somente depois retomar seeds reais subsequentes.

## Gates

Antes de qualquer implementação funcional:

- Issue relacionada atualizada;
- `stable-15jun` sincronizada e limpa;
- nenhuma execução real de Proventos/CSV/snapshots;
- testes de parser com fixture sanitizada e registro de 245 bytes;
- prova de idempotência;
- prova de que BRAPI não sobrescreve fatos COTAHIST;
- documentação de bootstrap mantida sincronizada.
