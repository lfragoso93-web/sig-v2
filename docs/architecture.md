# Arquitetura — SGI v2

> Última atualização: 06/10/2026.

## Objetivo

O SGI v2 calcula patrimônio, posição, custo, resultado, Proventos, rentabilidade e IRPF a partir de dados persistidos e contratos canônicos. Provedores externos pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados; páginas, KPIs, relatórios e cálculos financeiros não consultam providers diretamente.

## Fluxo financeiro principal

```text
bootstrap / sincronizadores autorizados
        ↓
assets + asset_prices + rate_history + fx_rates
asset_dividends + corporate_events
        ↓
transactions
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

`transactions` é a fonte canônica do lifecycle financeiro, inclusive Renda Fixa e Tesouro Direto. Não reintroduzir projeção paralela em `fixed_income_investments`.

## Princípios obrigatórios

### DB-first

- serviços financeiros leem dados persistidos;
- busca, detalhes, posições, relatórios, IRPF, Proventos e rentabilidade não consultam provider no read path financeiro;
- dados externos são persistidos antes de alimentar contratos financeiros;
- ausência de preço, FX ou benchmark é explícita e nunca vira zero, paridade fixa ou preço inventado.

### Contratos financeiros únicos

- `summary.v2` é a leitura consolidada canônica de resumo;
- `rentabilidade.v2` é a leitura pública canônica de rentabilidade;
- projetores compartilhados fornecem posição, custo e realizado;
- snapshots persistem a série histórica derivada;
- módulos futuros não podem recriar esses cálculos localmente.

### Idempotência e rastreabilidade

Bootstrap, seeds, sincronizações, migrations e rebuilds devem produzir estado lógico estável sem duplicar fatos financeiros. Operações reais devem registrar SHA/run_id/evidência quando o contrato exigir.

### Qualidade explícita

Cobertura parcial, preços ausentes, retornos estimados, fontes e datas efetivas ficam observáveis. Indisponibilidade não é convertida em número aparentemente válido.

## Proventos

Eventos monetários pertencem ao ativo e são persistidos em `asset_dividends`.

Direitos por carteira são projetados sob demanda a partir da posição histórica. Não existe materialização canônica de direitos por portfolio.

A prova assistida portfolio-scoped já demonstrou idempotência. A #226 aceitou essa evidência como suficiente para promoção controlada; execução global só deve ser reconsiderada diante de necessidade material nova em #216/#158.

## Eventos corporativos

Eventos pertencem ao ativo em `corporate_events`. Transações históricas não são mutadas para aplicar split, grupamento, bonificação, subscrição ou troca de ticker.

Eventos complexos podem permanecer `UNRECONCILED` até tratamento canônico.
Eventos materiais precisam estar reconciliados ou formalizados como `CONFLICT`
fail-closed no dataset aprovado; conflito não autoriza `MATCHED` sem evidência.

## Renda Fixa e Tesouro

### Tesouro Direto

- valuation DB-first por preço persistido;
- resolução case-insensitive validada;
- snapshots dedicados;
- ausência de PU necessário permanece explícita/fail-closed.

### Renda Fixa

- lifecycle derivado de `transactions`;
- valuation corrente usa motor dedicado de accrual/indexador;
- benchmark parcial/ausente não vira preço de mercado;
- TWR diário dedicado ainda pertence à #149.

A ausência de TWR dedicado não deve ser mascarada por retorno simples ou fallback anual rotulado como TWR.

## IRPF

O módulo anual consome operações/classes suportadas e permanece separado do valuation contábil. Classes não suportadas ficam explicitamente fora do cálculo até módulo dedicado.

O estado "DARF pago" armazenado apenas no frontend/localStorage não deve ser tratado como persistência fiscal auditável de servidor.

## Metas e Análise

A situação atual não é mais "goals intocável".

### Metas operacional

Durante a certificação assistida, schema/runtime/UI foram alinhados o suficiente para operações básicas. A migration runtime-safe de 10/09 corrigiu a divergência necessária para funcionamento atual.

Isso não transforma o desenho atual no contrato definitivo do domínio.

### Macroprojeto #246

O desenho definitivo deve decidir:

- taxonomia de metas;
- relação com `portfolio_class_targets`;
- campos persistidos versus calculados;
- histórico/evolução;
- concentração/diversificação/rebalanceamento;
- integração com Analysis Engine #360.

### Analysis Engine #360

Deve ser determinístico, DB-first e consumir contratos financeiros existentes sem duplicá-los.

### IA #361

Somente depois do Analysis Engine. IA é camada explicativa sobre DTO estruturado; não calcula números financeiros e não acessa banco/provider de forma irrestrita.

## Asset Detail

A superfície de detalhe de ativo já existe parcialmente e foi exercitada com histórico, Proventos e preço médio canônico. #58 permanece aberta para completar cobertura, DY, metadados, iconografia e responsividade junto da #351.

Nenhum provider deve ser chamado no render/read path para completar logos, histórico ou métricas.

## Bootstrap e rebuild

O fluxo canônico está detalhado em `docs/BOOTSTRAP_DATA_FLOW.md`.

Separar:

1. Initial Bootstrap;
2. Incremental Sync;
3. Full Market Rebuild;
4. Promotion Reconciliation (#158).
5. Real-data Certification (#384).

`full_market_rebuild` não substitui bootstrap inicial nem a reconciliação de promoção. Não repetir operações destrutivas já certificadas somente por checklist histórico.

## Readiness

Existem estados distintos:

1. ambiente não preparado;
2. ambiente apto a validação assistida;
3. ambiente pronto para dados reais.

Estado operacional certificado em 06/10/2026 para a identidade runtime vigente:

```text
user-test-readiness.v1=GO_ASSISTED
ready_for_real_data=true
/health=200
/ready=200
```

`GO_ASSISTED` não implica `/ready=200` e não satisfaz o contrato de promoção da
#384. O `/ready=200` atual existe porque houve evidência própria com `status=GO`
e um evento `PROMOTE` persistido para a identidade exata.

A decisão histórica da #227 e a promoção arquitetural da PR #362 já foram
concluídas. A fronteira corrente é persistente e append-only:

```text
evidência real-data-promotion-evidence.v1
        → plano determinístico + confirmação forte
        → advisory lock PostgreSQL + validação de stale plan
        → real_data_certification_events
        → leitor DB-first / relatório
        → integração fail-closed com /ready
```

A memória do processo não é autoridade. O último evento persistido determina o
estado auditável; promoção e revogação criam novos eventos, nunca alteram ou
apagam o histórico. O `/ready` resolve sua identidade esperada fora do log de
certificação e somente abre diante de promoção persistida exatamente compatível.
O evento `PROMOTE` vigente foi persistido e sobreviveu ao restart do backend.
Qualquer divergência futura de SHA, dataset ou schema volta a fechar o endpoint
até novo ciclo guardado. O contrato operacional está em
`docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`.

## Local x OCI

### Local

Ambiente oficial de desenvolvimento, correção, migrations de teste, suítes pesadas e certificação financeira.

### OCI

Backlog futuro sob #284; não integra o caminho atual de desenvolvimento ou a
ativação da #384. Quando retomado, deve homologar o SHA exato já certificado,
sem hotfix permanente na VM e sem remoção de volumes persistentes.

## Segurança e operação

- PostgreSQL, Redis e backend não devem ser expostos publicamente;
- Cloudflare Tunnel permanece o caminho preferido de aplicação no desenho OCI atual;
- segredos ficam fora do Git;
- rollback preserva volumes salvo reset explicitamente autorizado e respaldado por backup;
- migrations destrutivas e contrações físicas exigem gate próprio.

## Ordem arquitetural corrente

1. preservar a certificação vigente enquanto sua identidade continuar exata;
2. concluir #346 com Agent Skills versionadas;
3. gerar Certification Proof reproduzível em #347;
4. avançar #349, #348 e #350 em microblocos independentes;
5. tratar #365 antes de qualquer migration ampla de #364;
6. manter OCI/#284 como backlog futuro até retomada explícita.

## Backlog pós-GO por padrão

- #149 — TWR diário dedicado restante;
- #351/#90/#58 — UX/detalhe de ativo;
- #355–#359 — features auxiliares;
- #246/#360 — Metas + Analysis Engine;
- #361 — IA;
- #97 — OAuth.

#352 foi fechada apos validacao manual do seletor `Tipo de ativo` no modal de lancamento. #354 foi fechada após alinhamento da política de senha frontend/backend e só deve reabrir com regressão comprovada.
