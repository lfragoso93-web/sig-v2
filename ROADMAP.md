# Roadmap — SGI v2

> Última atualização: 06/10/2026.

## Estado do projeto

O SGI v2 está em fase de **pós-GO e hardening arquitetural**, com a baseline
funcional promovida para `main` pela PR #362 e o núcleo DB-first consolidado.

Estado registrado:

```text
GO_ASSISTED=true
ready_for_real_data=true
/health=200
/ready=200
```

Branch obrigatória: `stable-15jun`.

## Fase 1 — `PORTFOLIO-TEST-READY` (#303) — CONCLUÍDA

Objetivo concluido: congelar um SHA candidato funcional antes dos gates de dados reais.

Estado:

1. #363 fechado;
2. #352 fechado apos validacao manual do seletor `Tipo de ativo`;
3. #354 preservado fechado;
4. `PORTFOLIO-TEST-READY` registrado formalmente na #303;
5. `ready_for_real_data=false` permaneceu obrigatorio durante este gate
   funcional, antes da promocao persistente posterior da #384.

Não é necessário concluir #149, #351, #360, #361, OAuth, exportações ou calculadoras para fechar #303, desde que indisponibilidades sejam explícitas e não prejudiquem jornada crítica.

## Fase 2 — Proventos (#226) — CONCLUÍDA

A arquitetura e a implementação estão avançadas. O contrato vigente é `pre-prod-dividends-seed.v2`: eventos globais são persistidos exclusivamente em `asset_dividends` e os direitos de carteira são calculados sob demanda a partir das posições históricas, sem materialização por carteira. Já existe prova controlada portfolio-scoped e idempotente.

Decisão:

- aceitar portfolio-scoped como evidência operacional suficiente para o escopo de promoção controlada;
- não executar seed global mecanicamente;
- exigir global controlado somente se #216/#158 identificarem necessidade material nova.

## Fase 3 — gate agregado (#216) — CONCLUÍDA

Benchmarks e câmbio permanecem consolidados. A decisão de #226 foi consumida:
a evidência portfolio-scoped de Proventos é suficiente para a promoção
controlada, sem seed global mecânico. Global controlado só volta ao escopo se
#158 encontrar necessidade material nova.

## Fase 4 — promotion reconciliation (#158) — CONCLUÍDA

Executar apenas o delta necessário sobre SHA/dataset congelados:

- importação controlada se ainda necessária;
- rebuild apenas dos derivados necessários;
- reconciliar patrimônio, lifecycle, snapshots, rentabilidade, Proventos, Tesouro, Renda Fixa e IRPF;
- reconciliar eventos corporativos materiais ao dataset;
- restart/idempotência/persistência;
- eventual contração física somente com backup/gate explícito.

Não repetir destruições/rebuilds já certificados sem novo finding.

Estado: runtime Docker/Postgres, `user_test_readiness`, restart, persistência,
idempotência, eventos corporativos materiais e segurança #269 foram validados
localmente no SHA candidato publicado em `stable-15jun`.

## Fase 5 — OCI (#284) — BACKLOG FUTURO

OCI não faz parte do caminho atual. O escopo abaixo permanece como referência
para retomada futura de infraestrutura/cloud.

Validar:

- `APP_COMMIT_SHA == git rev-parse HEAD`;
- migrations aprovadas;
- Compose e portas;
- `/health` e semântica de `/ready`;
- Cloudflare Tunnel;
- restart/volumes/persistência;
- CPU/RAM/disco;
- segurança/resiliência aplicáveis.

Falhas de código retornam ao ambiente local; não há desenvolvimento permanente na VM.

## Fase 6 — GO / NO-GO (#227) — CONCLUÍDA

A decisão da #227 foi concluída e consumida pela promoção da PR #362.

A promoção arquitetural não altera automaticamente:

```text
ready_for_real_data=true
```

Qualquer mudança futura desse estado pertence ao contrato persistente e
auditável da #384.

## Fase 7 — enforcement arquitetural (#344) — CONCLUÍDA

Blocos concluídos e promovidos para `main`:

1. #345 Architecture Doctor — concluída e promovida pela PR #385;
2. #346 Agent Skills — concluída;
3. #347 Certification Proof — concluída pela PR #393;
4. #349 Deterministic Runtime — concluída pela PR #394;
5. #348 Authorization / Access Context — concluída pela PR #395;
6. #350 Reliable Async — concluída pela PR #396, com lease distribuído e
   decisão documentada de não introduzir outbox sem caso concreto.

Próxima fronteira: hygiene e upgrades Dependabot priorizados, nova baseline
técnica e somente então #365 antes de qualquer migration ampla da #364.

## Fase 8 — certificação persistente para dados reais (#384) — CONCLUÍDA

Fundação já promovida pelas PRs #386 e #387:

- evento append-only persistido e migration dedicada;
- leitor DB-first e relatório composto;
- evidência versionada `real-data-promotion-evidence.v1`;
- plano determinístico, confirmação forte e executor transacional sob advisory
  lock PostgreSQL;
- CLI dry-run por padrão, com escrita condicionada a `--execute` e à confirmação
  exata emitida no dry-run.

Prova PostgreSQL isolada concluída em 06/10/2026: concorrência serializada,
idempotência, rejeição de stale plan e reconstrução após restart.

Conclusão operacional em 06/10/2026:

1. identidade canônica derivada de backup consistente `pre-prod-backup.v3`;
2. evidência própria `real-data-promotion-evidence.v1` aprovada;
3. evento `PROMOTE` persistido para a identidade exata do runtime no SHA
   `3ab054f61e34f440dddf93c170259958243d58af`;
4. `/ready=200` e `ready_for_real_data=true` reconstruídos pela autoridade
   DB-first, inclusive após restart.

Integração concluída em 06/10/2026: `/ready` resolve ambiente, branch, SHA,
dataset e revision Alembic independentemente do evento, consulta a decisão
persistida e falha fechado em qualquer ausência ou divergência. O bootstrap em
memória permanece apenas diagnóstico.

Qualquer mudança posterior de environment, branch, SHA, dataset ou revision
Alembic invalida essa correspondência e exige novo ciclo completo. O contrato
permanece fail-closed em qualquer ausência, revogação ou divergência.

## Dívidas financeiras não bloqueantes por padrão

### #149 — TWR diário Tesouro/Renda Fixa

- Tesouro: valuation DB-first/snapshots dedicados avançados;
- Renda Fixa: valuation atual funcional, TWR diário dedicado ainda pendente.

Não fabricar retorno. Se TWR não existir, UI deve declarar indisponibilidade. Só vira blocker se o escopo aprovado do primeiro release exigir essa métrica.

### Eventos corporativos

Eventos portfolio-scoped já podem ser coletados. No dataset alvo, a varredura de
materialidade de 22/09/2026 não deixou evento material em `UNRECONCILED`: AMOB3
ficou formalizada como 1 `MATCHED` canônico + 1 `CONFLICT` revisável, e KLBN11
ficou em `CONFLICT` até existir evidência documental de liquidação fracionária
para eventual `MATCHED`.

## Backlog funcional classificado

| Issue | Estado | Relação com primeiro GO |
|---|---|---|
| #58 detalhe global do ativo | parcialmente implementada | não blocker automático |
| #90 UX Patrimônio | planejada | pós-GO |
| #246 Metas + Análise | Metas operacional parcial; macroprojeto planejado | não blocker automático |
| #351 UI/UX V2 | planejada | pós-GO |
| #352 seleção de classe | fechado | validada manualmente; nao blocker |
| #353 scroll | bug UX P2 | não blocker automático |
| #354 senha | fechado | não blocker enquanto frontend/backend seguirem alinhados |
| #355 taxonomia RF | planejada | pós-GO |
| #356 paginação | planejada | pós-GO |
| #357 export | planejada | pós-GO |
| #358 import B3 | planejada | pós-GO |
| #359 calculadoras | planejada | pós-GO |
| #360 Analysis Engine | planejada | pós-GO / depende #246 |
| #361 IA | planejada | pós-GO / depende #360/#246 |
| #97 OAuth | planejada | pós-GO |

## Estado por domínio

| Domínio | Estado |
|---|---|
| Core/Autenticação | 🟢 funcional em validação assistida |
| DB-first/provider boundary | 🟢 consolidado |
| Transações/lifecycle | 🟢 canônico |
| CSV | 🟢 certificado |
| Patrimônio/Resumo | 🟢 reconciliado |
| Snapshots/rebuild | 🟢 avançado/certificado |
| Tesouro | 🟢 valuation DB-first |
| Renda Fixa atual | 🟢 valuation dedicado |
| RF TWR diário | 🟠 #149 |
| Proventos `pre-prod-dividends-seed.v2` | 🟢 asset-based; direitos sob demanda; portfolio-scoped comprovado |
| Proventos gate amplo | 🟢 #226 portfolio-scoped suficiente |
| Eventos corporativos | 🟠 sem `UNRECONCILED` material; KLBN11 em `CONFLICT` revisável |
| IRPF suportado | 🟢 funcional |
| Metas operacional | 🟢 básico funcional |
| Análise/IA | ⚪ planejado |
| Usuários assistidos | 🟢 GO_ASSISTED |
| Dados reais amplos | 🟢 GO somente para a identidade runtime certificada pela #384; fail-closed em qualquer divergência |

## Governança

- não abrir PR para cada microcommit;
- não misturar Dependabot/toolchain no SHA candidato sem necessidade;
- Issues e documentação são fonte viva e devem ser atualizadas junto das decisões;
- README, ROADMAP e CHANGELOG permanecem sincronizados;
- PR para `main` somente ao fechar um macrobloco estrutural certificado.
