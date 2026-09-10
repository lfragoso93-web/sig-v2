# Fluxo canônico de bootstrap e carga de dados — SGI v2

> Documento arquitetural canônico para reconstrução inicial, sincronização incremental e rebuild de dados globais. Qualquer seed, backfill, rebuild ou Central de Bootstrap deve respeitar este fluxo.

Atualizado em 10/09/2026 para separar bootstrap técnico, `GO_ASSISTED` e promoção para dados reais.

## Objetivo

Evitar que estágios de carga sejam executados fora de ordem, sobrescrevam dados certificados ou misturem fontes com responsabilidades diferentes.

Este documento distingue quatro operações que não são equivalentes:

1. **Initial Bootstrap** — construção de uma base vazia ou recém-reconstruída;
2. **Incremental Sync** — atualização rotineira de dados já persistidos;
3. **Full Market Rebuild** — reconstrução de derivados/cobertura sobre uma base global já preparada;
4. **Promotion Reconciliation** — delta final e controlado executado sobre SHA/dataset candidato depois dos gates de certificação.

`full_market_rebuild` não substitui Initial Bootstrap nem Promotion Reconciliation.

## Princípios

- runtime financeiro é DB-first;
- providers participam apenas de bootstrap, ingestão, sincronização ou reconciliação explícitas;
- dados de carteira nunca devem criar silenciosamente fatos globais;
- cada domínio possui fonte canônica e fallbacks explicitamente limitados;
- operações idempotentes preferem escrita conservadora e nunca fazem downgrade silencioso de autoridade;
- evidência já certificada deve ser reutilizada; não repetir operação destrutiva apenas por checklist histórico;
- `GO_ASSISTED` permite validação controlada e não equivale a `ready_for_real_data=true`;
- `ready_for_real_data=true` somente pode ser avaliado após #226 -> #216 -> #158 -> #227.

## Ambientes

### Local

Ambiente primário de desenvolvimento, correção e certificação pesada. O SHA candidato nasce e é validado aqui.

### OCI

Ambiente de homologação do SHA já certificado localmente. OCI valida deploy, migrations, persistência, restart, recursos, rede, tunnel e smoke. Falha de código encontrada na OCI deve ser corrigida localmente e resultar em novo SHA; não se desenvolve na VM.

## 1. Universo B3 — autoridade e precedência

Para ativos B3 (`ACAO`, `FII`, `ETF_NACIONAL`, `BDR`):

1. B3 COTAHIST é baseline histórico oficial;
2. COTAHIST fornece o máximo possível de identidade/metadados oficiais;
3. BRAPI enriquece/atualiza campos complementares;
4. BRAPI não apaga fatos oficiais persistidos do COTAHIST;
5. Yahoo não é fonte primária do universo B3.

O estágio `b3_baseline` do `system-bootstrap.v4` precede `asset_catalog`. BRAPI enriquece B3 já persistida e mantém seu papel canônico onde o contrato do domínio assim definir, como CRIPTO suportado.

## 2. Ordem canônica do Initial Bootstrap

### Fase 0 — Schema e infraestrutura

- migrations/Alembic no head aprovado para o ambiente;
- PostgreSQL/Redis/serviços saudáveis;
- identidade operacional branch/SHA/run_id quando aplicável;
- nenhuma promoção manual de readiness.

### Fase 1 — Catálogos globais

- B3: COTAHIST-first, BRAPI enrichment;
- Cripto: universo suportado pelo contrato vigente;
- Tesouro: catálogo oficial dedicado;
- demais classes: fonte canônica própria.

Nenhum catálogo depende de carteira de usuário para existir.

### Fase 2 — Históricos globais de preços

- B3: COTAHIST em `asset_prices`;
- Tesouro: fonte oficial dedicada;
- Cripto/outras classes: provider dedicado por capacidade;
- backfill genérico somente onde não houver provider/bootstrap dedicado.

### Fase 3 — Séries auxiliares

Benchmarks, taxas macroeconômicas e câmbio preservam fontes canônicas e fallbacks governados.

### Fase 4 — Proventos

Tabela canônica: `asset_dividends`.

- direitos pertencem ao ativo e são projetados para carteira sob demanda;
- nenhuma materialização por carteira;
- BRAPI é authoritative quando possui cobertura válida;
- Yahoo é fallback de cobertura, não concorrente do mesmo evento;
- valores usam normalização canônica/`Decimal` compatível com `Numeric(18, 8)`.

A certificação assistida já comprovou seed `portfolio-scoped` e idempotência. O gate #226 decide se essa estratégia é suficiente para promoção ou se haverá global controlado.

### Fase 5 — Eventos corporativos

Tabela canônica: `corporate_events`.

Eventos pertencem ao ativo. Transações históricas não são mutadas para "aplicar" eventos. Eventos materiais ao dataset de promoção devem estar reconciliados antes do GO; não é obrigatório reconciliar todo o universo global se isso não for requisito do escopo aprovado.

### Fase 6 — Auditoria de cobertura

Auditar cobertura temporal, gaps, duplicidades, órfãos, fontes, lifecycle e blockers por domínio.

### Fase 7 — Dados de carteira

Há duas políticas distintas:

- **validação assistida:** pode usar carteira/dados controlados quando `GO_ASSISTED` autorizar;
- **abertura ampla real:** somente depois dos gates #226/#216/#158 e decisão #227.

Importação não pode descobrir provider silenciosamente nem substituir catálogo global.

### Fase 8 — Derivados de carteira

Posições, custo/preço médio, direitos de Proventos e efeitos de eventos corporativos usam motores canônicos, sem duplicar fatos globais.

### Fase 9 — Snapshots, valuation e TWR

Executar após transações e cobertura necessária. Gaps devem permanecer explícitos; contratos dedicados como RF/Tesouro não recebem fallback silencioso de mercado.

### Fase 10 — Reconciliação

Validar patrimônio, rentabilidade, Proventos, Tesouro, Renda Fixa, IRPF suportado, restart/persistência/idempotência e provider-boundary.

Esta fase pode produzir `GO_ASSISTED`, mas não promove dados reais por si só.

## 3. Promotion Reconciliation

Quando #303 estiver funcionalmente pronto e #226/#216 liberarem o gate de dados globais, #158 executa somente o delta necessário sobre SHA/dataset congelados:

- importação controlada quando ainda necessária;
- rebuild somente dos derivados necessários;
- reconciliação financeira final;
- eventos corporativos materiais ao dataset;
- restart/idempotência/persistência;
- eventual contração física somente com backup e autorização.

A evidência é entregue à #227. Somente #227 registra GO/NO-GO amplo.

## 4. Sincronização incremental

Não repetir Initial Bootstrap indiscriminadamente.

- COTAHIST complementa períodos ausentes sem downgrade;
- BRAPI enriquece/atualiza dentro de sua responsabilidade;
- backfills operam em gaps comprovados;
- providers dedicados prevalecem sobre backfill genérico;
- Proventos seguem autoridade/fallback do domínio;
- fallbacks ficam observáveis em source/evidência.

## 5. Full Market Rebuild

É manutenção/reconstrução sobre base preparada. Pode atuar em preços, Tesouro, benchmarks, snapshots/TWR, manutenção e auditoria de cobertura conforme contrato vigente.

Não deve:

- bootstrapar base vazia;
- criar silenciosamente todos os catálogos;
- contornar gates de Proventos/eventos;
- importar CSV real;
- substituir #158;
- ser executado globalmente apenas para repetir evidência já certificada.

## 6. Matriz de autoridade

| Domínio | Fonte primária/canônica | Complementar/fallback | Escrita principal |
| --- | --- | --- | --- |
| Catálogo B3 | B3 COTAHIST | BRAPI enrichment | `assets` |
| Histórico B3 | B3 COTAHIST | sem overwrite genérico | `asset_prices` |
| Cripto | contrato BRAPI/universo suportado | capability explícita | `assets`/preços |
| Tesouro | fonte oficial | contrato dedicado | catálogo/preços |
| Benchmarks | fontes oficiais | fallback governado | séries/taxas |
| Câmbio | fonte canônica vigente | fallback governado | FX |
| Proventos | BRAPI | Yahoo fallback-only | `asset_dividends` |
| Eventos corporativos | provider canônico | fallback explícito | `corporate_events` |
| Transações | entrada do usuário | resolução por catálogo | `transactions` |
| Posições | cálculo interno | — | derivados |
| Snapshots/TWR | cálculo interno | — | snapshots |

## 7. Gates operacionais

Antes de cada operação real:

- Issue relacionada atualizada;
- branch `stable-15jun` e SHA conhecidos;
- working tree limpa no ambiente de desenvolvimento;
- dependências anteriores concluídas;
- run_id/evidência quando exigido;
- somente tabelas autorizadas;
- comparação antes/depois;
- interrupção no primeiro blocker não reconciliado.

Para OCI, adicionalmente: checkout deve corresponder exatamente ao SHA certificado localmente.

## 8. Relação com Issues

- #303 — certificação funcional/`GO_ASSISTED`;
- #226 — decisão operacional de Proventos;
- #216 — gate agregado;
- #158 — Promotion Reconciliation;
- #227 — GO/NO-GO amplo;
- #284 — homologação OCI;
- #129 — eventos corporativos;
- #253 — futura Central de Bootstrap;
- #130 — evolução BRAPI.

## 9. Estado atual — 10/09/2026

Já comprovado:

- COTAHIST-first para B3;
- Tesouro oficial;
- benchmarks/câmbio isolados;
- Proventos globais asset-based e prova portfolio-scoped idempotente;
- eventos corporativos globais com seed portfolio-scoped disponível;
- DB-first/provider-boundary;
- carteira assistida com CSV/rebuild/reconciliações;
- `user-test-readiness.v1 = GO_ASSISTED` sem blockers/warnings na evidência registrada.

Estado de readiness:

```text
/health = 200
/ready = 503
GO_ASSISTED = true
ready_for_real_data = false
```

Pendências de promoção:

1. fechar rodada #303 e congelar SHA;
2. decidir #226;
3. fechar #216;
4. executar delta #158;
5. homologar o mesmo SHA na OCI;
6. #227 emitir GO/NO-GO;
7. somente após GO avaliar `ready_for_real_data=true`.
