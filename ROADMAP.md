# Roadmap — SGI v2

> Última atualização: 23/09/2026.

## Estado do projeto

O SGI v2 está em fase de **certificação assistida e preparação do primeiro GO controlado**, com o núcleo DB-first consolidado.

Estado registrado:

```text
GO_ASSISTED=true
ready_for_real_data=false
/health=200
/ready=503
```

Branch obrigatória: `stable-15jun`.

## Fase 1 — `PORTFOLIO-TEST-READY` (#303) — CONCLUÍDA

Objetivo concluido: congelar um SHA candidato funcional antes dos gates de dados reais.

Estado:

1. #363 fechado;
2. #352 fechado apos validacao manual do seletor `Tipo de ativo`;
3. #354 preservado fechado;
4. `PORTFOLIO-TEST-READY` registrado formalmente na #303;
5. `ready_for_real_data=false` permanece obrigatorio.

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

## Fase 4 — promotion reconciliation (#158) — AGORA

Executar apenas o delta necessário sobre SHA/dataset congelados:

- importação controlada se ainda necessária;
- rebuild apenas dos derivados necessários;
- reconciliar patrimônio, lifecycle, snapshots, rentabilidade, Proventos, Tesouro, Renda Fixa e IRPF;
- reconciliar eventos corporativos materiais ao dataset;
- restart/idempotência/persistência;
- eventual contração física somente com backup/gate explícito.

Não repetir destruições/rebuilds já certificados sem novo finding.

## Fase 5 — homologação OCI (#284)

OCI recebe exatamente o SHA certificado localmente.

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

## Fase 6 — GO / NO-GO (#227)

A #227 consome as evidências de #303, #226, #216, #158 e homologação OCI.

Somente GO formal permite avaliar:

```text
ready_for_real_data=true
```

Depois do GO, preparar PR estrutural `stable-15jun` → `main` do macrobloco certificado.

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
| Dados reais amplos | 🔴 NO-GO atual |

## Governança

- não abrir PR para cada microcommit;
- não misturar Dependabot/toolchain no SHA candidato sem necessidade;
- Issues e documentação são fonte viva e devem ser atualizadas junto das decisões;
- README, ROADMAP e CHANGELOG permanecem sincronizados;
- PR para `main` somente ao fechar um macrobloco estrutural certificado.
