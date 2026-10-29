# Arquitetura — SGI v2

> **Última Atualização:** 29/10/2026.
> **Relatório Oficial de Oportunidades de Melhoria:** [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md).
> **Manuais dos Subprojetos:** [`backend/README.md`](../backend/README.md) | [`frontend/README.md`](../frontend/README.md).

## Objetivo

O SGI v2 calcula patrimônio, posição, custo, resultado, Proventos, rentabilidade e IRPF a partir de dados persistidos e contratos canônicos. Provedores externos pertencem a bootstrap, ingestão, sincronização ou reconciliação explicitamente autorizados; páginas, KPIs, relatórios e cálculos financeiros não consultam providers diretamente.

## Fluxo financeiro principal

```text
bootstrap / sincronizadores autorizados (assíncronos com Redis lock)
        ↓
assets + asset_prices + rate_history + fx_rates + asset_dividends + corporate_events
        ↓
transactions (livro-razão canônico único)
        ↓
projeções canônicas de posição, custo e realizações
        ↓
valuation dedicado por classe (Ações, FIIs, Renda Fixa, Tesouro, Cripto, Internacional)
        ↓
PortfolioSnapshot + PortfolioClassSnapshot (escritor único canônico)
        ↓
summary.v2 + rentabilidade.v2 + leitores históricos + Analysis Engine (#360)
        ↓
Resumo / Patrimônio / Rentabilidade / Proventos / IRPF / AnalisePage (IA #361) / AssetDetailDrawer (#58)
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

### Runtime determinístico

Lógica financeira sensível a datas usa o `Clock` canônico quando migrada;
Proventos é a primeira vertical protegida por `FrozenClock`. Configuração
crítica falha no startup sem registrar valores sensíveis, e budgets de queries
protegem leitores prioritários contra regressões N+1. O contrato operacional
está em `docs/DETERMINISTIC_RUNTIME.md`.

### Autorização com escopo explícito

Dados sensíveis por carteira não confiam em `portfolio_id` livre vindo do
cliente. Verticais migradas recebem `PortfolioAccessContext`, declaram a
permissão no service e aplicam ownership no repository. Dividendos é a primeira
vertical completa. Jobs e CLIs devem usar identidade de usuário comprovada ou
contexto sistêmico com finalidade explícita; bypass implícito é proibido. O
contrato e o inventário de migração estão em `docs/ACCESS_CONTEXT.md`.

### Processamento assíncrono confiável

Jobs globais de escrita não podem depender apenas de `max_instances=1`, que é
local ao processo. O fechamento diário de preços é a primeira vertical com
lease Redis fail-closed, TTL e liberação por token. A decisão arquitetural atual
não adota transactional outbox: os efeitos assíncronos examinados são derivados
e reconstruíveis, sem publicação externa que justifique nova tabela e worker.
Inventário, riscos e gatilhos de reavaliação estão em `docs/RELIABLE_ASYNC.md`.

## Proventos

Eventos monetários pertencem ao ativo e são persistidos em `asset_dividends`.

Direitos por carteira são projetados sob demanda a partir da posição histórica. Não existe materialização canônica de direitos por portfolio.

A prova assistida portfolio-scoped já demonstrou idempotência. A #226 aceitou essa evidência como suficiente para promoção controlada; execução global só deve ser reconsiderada diante de necessidade material nova em #216/#158.

## Eventos corporativos

Eventos pertencem ao ativo em `corporate_events`. Transações históricas não são mutadas para aplicar split, grupamento, bonificação, subscrição ou troca de ticker.

Eventos complexos podem permanecer `UNRECONCILED` até tratamento canônico.
Eventos materiais precisam estar reconciliados ou formalizados como `CONFLICT`
fail-closed no dataset aprovado; conflito não autoriza `MATCHED` sem evidência.
O contrato para incorporações, cisões com ativos destino e resgates está em
[`CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md`](CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md).
O classificador B3 e o projetor puro para transformacoes nao monetarias
estao implementados em memoria, sem persistencia ou integracao financeira;
os candidatos reais continuam fora do efeito financeiro. O processador
portfolio-scoped de troca de ticker nao deve ser reutilizado como substituto.

## Renda Fixa e Tesouro

### Tesouro Direto

- valuation DB-first por preço persistido;
- resolução case-insensitive validada;
- snapshots dedicados;
- cupons e amortizações monetários usam eventos globais em `asset_dividends`,
  com direito por carteira derivado de `transactions`, e entram uma única vez
  no TWR do snapshot;
- ausência de PU necessário permanece explícita/fail-closed.

### Renda Fixa

- lifecycle derivado de `transactions`;
- valuation corrente usa motor dedicado de accrual/indexador;
- benchmark parcial/ausente não vira preço de mercado;
- após uma lacuna de benchmark, a cadeia TWR materializada permanece
  `incomplete_history` mesmo se a cobertura voltar; patrimônio segue auditável,
  mas retornos mensal e acumulado não são promovidos como oficiais;
- TWR diário dedicado integra `PortfolioClassSnapshot`, com aportes e resgates
  tratados como fluxos externos e oracles para resgate parcial e múltiplas
  aplicações por produto/indexador.

Novos contratos recebem o tratamento fiscal a partir de `product_type`; a API
normaliza `tax_exempt` e nao aceita escolha manual como regra canonica. CDB,
RDB, LC, debenture comum, Letra Financeira e Outro sao tributaveis pela tabela
regressiva; LCI, LCA, LIG, CRI, CRA e debenture incentivada sao classificados
como isentos, sujeitos aos requisitos legais da emissao e do titular. A tela de
lancamento pede o nome completo do titulo (incluindo emissor), indexador e taxa;
emissor deixa de ser campo separado. Liquidez diaria limpa e oculta vencimento
e carencia. Contratos legados preservam emissor armazenado e podem ser
reutilizados quando o nome informado identifica esse emissor.

A #149 permanece aberta para evidência por conta/carteira da posição de custódia
na manhã de pagamento e para base tributável/IRRF por lote. A regra oficial de
elegibilidade foi identificada; detalhes em
`docs/TREASURY_CASH_EVENT_SOURCE_AUDIT.md`. Certificação de identidade runtime
é gate de promoção operacional para dados reais, separada do desenvolvimento
da Issue. Ausência de PU, benchmark ou calendário não deve ser mascarada por
retorno simples, evento inferido ou fallback rotulado como TWR.

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

### Analysis Engine (#360) — Implementado

O Analysis Engine opera de modo determinístico e DB-first, consumindo `summary.v2`, posições consolidadas e retornos históricos para calcular alocação por classes, diversificação e métricas de risco sem duplicar regras contábeis nem consultar provedores externos.

### Camada de IA (#361) — Implementada

A camada de Inteligência Artificial opera como explicador e sintetizador executivo em linguagem natural sobre o DTO estruturado gerado pelo Analysis Engine (`AnalisePage.tsx`). A IA não computa valores financeiros, não gera alucinações matemáticas e não possui autoridade para consultar o banco de dados ou a internet de forma irrestrita.

### Autenticação Google OAuth 2.0 e MFA TOTP (#97) — Implementado

Suporte a autenticação moderna via Google OAuth 2.0 e Segundo Fator de Autenticação (MFA via app autenticador / TOTP) governado no backend e persistido no schema Alembic sob a revisão `20261022_auth_oauth_mfa`.

## Ferramentas de Simulação (#359) — Implementadas

As ferramentas da #359 operam como simulações isoladas na rota `/carteira/ferramentas/*` (`IncomeCalculatorPage.tsx` e `FixedIncomeCalculatorPage.tsx`), sem efetuar leitura ou escrita no estado persistido da carteira:
- **Calculadora de Rendimentos:** Projeta juros compostos e aportes futuros.
- **Simulador de Renda Fixa:** Compara títulos calculando o tratamento tributário regressivo ou isenção de forma automática pelo tipo de produto (conforme taxonomia canônica). Premissas, fontes e fórmulas estão documentadas em `docs/TOOLS_CALCULATORS.md`.

## Asset Detail Drawer (#58 / #351) — Implementado

A gaveta consolidada lateral `AssetDetailDrawer.tsx` provê inspeção completa de qualquer ativo sob custódia, estruturada em abas:
- **Visão Geral:** Cotação corrente, variação diária, preço médio e métricas da posição.
- **Indicadores Fundamentalistas:** Painel de indicadores adaptados por classe de ativo (Ações, FIIs, BDRs, ETFs e Tesouro Direto), com histórico de proventos e múltiplos de mercado.
- **Gráfico de Preços:** Séries temporais persistidas com seletor de períodos (1M, 6M, 1A, Tudo).
- **Proventos & Eventos Corporativos:** Histórico oficial do ativo e split/grupamento.

Nenhum provedor externo é acionado no fluxo de renderização (`read path`) para completar logos, cotações ou indicadores.

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

Esse registro é histórico e vinculado à identidade certificada em 06/10/2026.
Na inspeção de 16/10/2026, o checkout publicado era
`b37661921e3a8455f45c8b676b28955d6ad3d0ea`, enquanto o runtime `testing`
reportava uma identidade diferente e dataset vazio. `/health=200` e `/ready=503`
com `runtime_identity_error`; não considerar o checkout atual certificado.
Ver `docs/DEVELOPMENT_BASELINE_2026-10-16.md` para a fotografia completa.

`GO_ASSISTED` não implica `/ready=200` e não satisfaz o contrato de promoção da
#384. `/ready=200` só é válido quando há evidência própria com `status=GO` e um
evento `PROMOTE` persistido para a identidade runtime exata.

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

1. confirmar os findings da #408 com uma execução CodeQL posterior à correção
   integrada pela #413 e aos testes da #419;
2. validar o ciclo de backup e restore apenas em banco isolado para fechar o
   escopo residual da #83;
3. concluir GOV-07 da #293 e alinhar Issues/documentação com o código atual;
4. depois, selecionar uma única entrega de produto pós-GO;
5. manter OCI/#284 como backlog futuro até retomada explícita.

As Issues #365 e #364 foram fechadas em 08/10/2026; não fazem mais parte da
sequência corrente. A higiene de dependências priorizada também foi integrada.

## Backlog pós-GO e Status de Implementação

Com as entregas consolidadas no branch `stable-15jun`:
- **Implementados:**
  - Analysis Engine (#360) e Camada de IA (#361) com `AnalisePage.tsx`;
  - Autenticação Google OAuth 2.0 e MFA TOTP (#97);
  - Gaveta consolidada de Detalhe de Ativo (#58 / #351);
  - Taxonomia de Renda Fixa e associadores (#355);
  - Simuladores e calculadoras financeiras (#359) em `/carteira/ferramentas/*`;
  - Catálogo e histórico de ativos internacionais (`366ae927`);
  - Tabela oficial de proventos (`dea616ee`).
- **Fechadas com validação:** #352 (seletor de tipo de ativo), #354 (alinhamento de senha), #363, #364, #365.
- **Backlog Técnico Vigente (Oportunidades Mapeadas):**
  - O backlog arquitetural, de integridade contábil e resiliência está formalizado em [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) (19 oportunidades catalogadas, OP-01 a OP-19).
  - #149 — Posição elegível por carteira e tributação por lote de cupons/amortizações.
  - #284 — Homologação da infraestrutura em nuvem OCI (preservada como backlog futuro).


## Lancamentos de cripto e historico de mercado

A compra/venda manual ou importada pode ser registrada para ativo CRIPTO
presente no catalogo persistido. A completude do historico de precos nao e uma
pre-condicao para persistir o fato do usuario: `HISTORY_END_UNAVAILABLE` e
outros status continuam informando cobertura incompleta a valuation, serie
historica e readiness, sem serem promovidos a cobertura completa nem usados
para inventar precos. Tickers fora do catalogo continuam bloqueados; fixtures
sinteticas exigem proveniencia de certificacao propria.
