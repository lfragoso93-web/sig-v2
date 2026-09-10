# Gate de readiness para testes assistidos

Atualizado em 10/09/2026.

Issue-mãe: #227  
Gate funcional: #303  
Branch obrigatória: `stable-15jun`

## Objetivo

O gate `user-test-readiness.v1` consolida sinais operacionais para decidir se o
SGI v2 pode receber rodadas assistidas com usuários convidados e massa
controlada.

Ele não substitui `/ready`, não representa readiness de produção e não autoriza
abertura ampla com dados reais. O ambiente continua `ready_for_real_data=false`
até a decisão formal dos gates #226, #216, #158 e #227.

## Estado consolidado em 10/09/2026

Resultado vigente da validação local:

```text
schema_version=user-test-readiness.v1
status=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
blockers=[]
warnings=[]
```

Baseline de governança no início do rebaseline:  
`9644a643f70d9126c7d07bfbac9231320515ee40`.

Interpretação:

- **GO** para validação assistida com usuários/controladores, contas de teste,
  carteiras fictícias/descartáveis e massa de homologação acompanhada;
- **NO-GO** para abertura ampla com dados reais;
- **NO-GO** para promover manualmente `ready_for_real_data=true`;
- falhas encontradas em rodada assistida devem virar Issues pequenas e
  rastreáveis antes de qualquer promoção de readiness.

## Como executar

No ambiente Docker:

```bash
docker compose run --rm backend python -m app.cli.user_test_readiness
```

Como SuperAdmin:

```text
GET /api/v1/admin/bootstrap/user-test-readiness
```

## Contrato

O relatório retorna:

- `schema_version`: sempre `user-test-readiness.v1`;
- `go_for_assisted_user_tests`: libera ou bloqueia rodada assistida;
- `ready_for_real_data`: espelha o gate real, sem promovê-lo;
- `status`: `GO_ASSISTED` ou `NO_GO`;
- `checks`: verificações com `code`, `status`, `detail` e `severity`;
- `counts`: contagens críticas de tabelas;
- `blockers`: falhas impeditivas;
- `warnings`: pendências não impeditivas para rodada assistida;
- `safety`: garantias de execução read-only.

## Checks atuais

- `database_inventory`: exige inventário pre-prod sem findings bloqueantes e sem
  tabelas não classificadas;
- `goals_runtime_schema`: exige a revision runtime-safe
  `20260910_goals_runtime`;
- `assisted_test_data_present`: exige usuários, carteiras e transações;
- `market_history_present`: exige catálogo e histórico de preços;
- `snapshot_history_present`: alerta se não houver snapshots;
- `dividends_seed_present`: alerta se não houver Proventos globais;
- `corporate_events_seed_present`: alerta se não houver eventos corporativos;
- `real_data_gate_closed`: confirma que dados reais continuam fechados;
- `automatic_bootstrap_policy`: confirma bootstrap automático desligado no
  ambiente de teste assistido.

## Evidência runtime local

Contagens observadas na execução de 10/09/2026:

```text
users=6
portfolios=5
transactions=332
assets=3684
asset_prices=4404638
portfolio_snapshots=536
asset_dividends=184
corporate_events=123
goals=2
```

Essas contagens são evidência do ambiente de validação observado naquele SHA;
não constituem contrato permanente nem devem ser usadas como expectativa fixa
para futuras execuções.

## Evidências que sustentam o GO assistido

A decisão `GO_ASSISTED` está apoiada por evidências já registradas na #303 e nos
runbooks de certificação:

- suíte backend completa registrada com `1880 passed, 1 skipped, 10 warnings`;
- frontend validado com instalação limpa, typecheck, lint, Vitest e build;
- carteira sintética multiclasse reproduzível e reconciliador independente;
- CSV sintético validado em dry-run, importação, replay, invalidade,
  anti-duplicidade, rollback/atomicidade e rebuild;
- valuation/snapshot canônicos reconciliados para mercado, Tesouro e Renda Fixa
  dentro das fronteiras suportadas;
- Redis fail-open e persistência PostgreSQL/volumes testados por restart;
- smoke UI autenticado e jornadas básicas percorridas;
- Proventos escopados para carteira assistida executados com prova de
  idempotência;
- IRPF das classes atualmente suportadas validado sem transformar classes fora
  de escopo em zero silencioso;
- `ready_for_real_data=false` preservado durante todo o processo.

## Fronteira de Proventos

O estado atual precisa distinguir duas situações:

### Carteira assistida / escopo controlado

Já existe evidência de execução escopada por carteira com:

- universo reduzido aos ativos elegíveis presentes nas transações da carteira;
- persistência somente em `asset_dividends`;
- segunda execução sem escrita física quando a fonte/estado não mudou;
- integridade e estado final estáveis.

Esse resultado é suficiente para continuar a validação assistida da carteira
controlada.

### Gate global para dados reais

A execução escopada **não fecha automaticamente #226/#216/#158** e não equivale
a certificação de uma varredura global. A estratégia operacional final de
Proventos deve ser decidida/registrada nos gates de dados reais antes da
promoção de `ready_for_real_data=true`.

## Fronteira de TWR e Renda Fixa

- valuation atual de Renda Fixa pode operar pelo contrato dedicado quando há
  cobertura qualificada suficiente;
- indisponibilidade de TWR diário dedicado de Renda Fixa continua explícita e é
  governada pela #149;
- retorno simples, fallback anual ou série artificial não podem ser promovidos
  a TWR oficial para satisfazer o gate;
- ausência de TWR dedicado, por si só, não invalida o GO assistido quando a UI
  publica corretamente a indisponibilidade.

## Interpretação do `GO_ASSISTED`

`GO_ASSISTED` permite:

- iniciar ou continuar testes acompanhados com usuários convidados;
- usar contas de teste e carteiras fictícias/descartáveis;
- validar CSV sintético/controlado;
- validar a carteira de homologação real-controlada somente no processo
  acompanhado e documentado;
- registrar bugs de UX, contrato, integração e finanças em Issues pequenas.

`GO_ASSISTED` não permite:

- abertura ampla para usuários com dados reais;
- seed real global fora de janela autorizada;
- promoção manual de readiness;
- considerar dado parcial/indisponível como zero;
- transformar resultado de homologação em declaração fiscal ou financeira
  oficial;
- pular #226, #216, #158 ou #227.

## Critérios de continuidade da rodada assistida

A rodada pode continuar enquanto:

- o gate retornar `GO_ASSISTED`;
- não houver blocker P0/P1 aberto afetando autenticação, segregação de
  carteiras, transações, CSV, patrimônio, rentabilidade, Proventos ou IRPF;
- o runtime esteja no SHA declarado da `stable-15jun`;
- a documentação permaneça alinhada ao comportamento observado;
- nenhum opt-in real seja ativado fora da Issue/gate correspondente.

## Critérios de bloqueio

Interromper a rodada e manter `ready_for_real_data=false` quando houver:

- uso acidental de dado real fora do escopo controlado;
- divergência financeira material sem explicação;
- chamada a provider em GET/cálculo financeiro comum;
- perda de dados após restart;
- acesso cruzado entre usuários/carteiras;
- exposição de superfície SuperAdmin a usuário comum;
- seed/importação real fora do gate autorizador;
- documentação ou identidade de SHA divergindo do runtime de certificação.

## Próximos gates

A sequência canônica para avaliar `ready_for_real_data=true` é:

1. concluir a rodada assistida e o marco formal `PORTFOLIO-TEST-READY` da #303;
2. decidir/certificar a estratégia operacional final de Proventos na #226;
3. reconciliar o gate agregado #216;
4. executar importação/rebuild/reconciliação operacional da #158;
5. produzir decisão formal GO/NO-GO na #227;
6. somente então avaliar `ready_for_real_data=true` e homologação final OCI.

Itens como persistência auditável de DARF paga, TWR completo de Renda Fixa,
redesign amplo de UX, Analysis Engine e IA devem permanecer em suas Issues
próprias e só bloqueiam a promoção quando representarem risco explícito para a
jornada real que está sendo certificada.
