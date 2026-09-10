# Continuidade de desenvolvimento — SGI v2

> Documento obrigatório para retomar desenvolvimento. Atualizado em 10/09/2026.

## Baseline atual

Branch obrigatória: `stable-15jun`.

Estado de governança após GOV-01..05:

- núcleo financeiro DB-first consolidado;
- certificação funcional em `GO_ASSISTED`;
- `ready_for_real_data=false`;
- `/health=200`;
- `/ready=503` enquanto o gate amplo permanecer fechado;
- documentação raiz rebaselined para o estado atual;
- OCI definida como ambiente de homologação do SHA exato certificado localmente.

## Ordem obrigatória de trabalho

1. revisar Issue relacionada e estado real do código antes de qualquer funcionalidade;
2. confirmar `stable-15jun`, HEAD remoto/local e working tree limpa;
3. avaliar impacto arquitetural e consumidores;
4. dividir implementação em microblocos;
5. testar localmente;
6. atualizar Issue/documentação viva;
7. informar SHA completo e próximo bloco;
8. abrir PR para `main` apenas ao fechar macrobloco estrutural certificado.

## Estado de readiness

```text
schema_version=user-test-readiness.v1
status=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
```

`GO_ASSISTED` permite usuários convidados e massa sintética/controlada. Não autoriza abertura ampla com dados reais.

## Cadeia de promoção

```text
#303
  ↓
#226
  ↓
#216
  ↓
#158
  ↓
OCI: homologação do SHA exato
  ↓
#227 GO / NO-GO
```

Somente após GO formal da #227 avaliar `ready_for_real_data=true`.

## Pendências de curto prazo

### #303 — PORTFOLIO-TEST-READY

- concluir rodada assistida sem P0/P1 crítico;
- revalidar #352 e #354;
- congelar SHA candidato;
- registrar decisão formal.

### #226/#216/#158

- consumir evidências já certificadas;
- evitar repetir seeds/rebuilds destrutivos por checklist histórico;
- executar somente o delta ainda necessário;
- reconciliar eventos corporativos materiais ao dataset.

### #284 — OCI

- checkout do SHA candidato exato;
- `APP_COMMIT_SHA == git rev-parse HEAD`;
- migrations aprovadas;
- smoke, tunnel, restart, persistência, recursos e segurança/resiliência;
- nenhuma correção permanente diretamente na VM.

## Arquitetura a preservar

- `transactions` é a fonte canônica do lifecycle financeiro;
- Renda Fixa e Tesouro não recriam projeção paralela em `fixed_income_investments`;
- `summary.v2`, `rentabilidade.v2`, snapshots e projetores de posição/custo são contratos canônicos;
- provider não participa de GETs/cálculos financeiros;
- ausência de preço/FX/benchmark não vira zero/fallback inventado;
- Proventos pertencem ao ativo em `asset_dividends`;
- direitos de Proventos por carteira são calculados sob demanda;
- eventos corporativos pertencem ao ativo em `corporate_events`;
- transações históricas não são mutadas para aplicar evento;
- bootstrap/rebuild/sync são operações explícitas e auditáveis.

## Estado funcional útil

- CSV canônico certificado em dry-run/import/replay/invalid/atomicidade/rebuild;
- carteira assistida exercitada com múltiplas classes;
- Tesouro DB-first e snapshots dedicados;
- Renda Fixa com lifecycle transaction-derived e valuation dedicado;
- Proventos portfolio-scoped idempotentes;
- IRPF funcional para classes suportadas;
- Metas básica operacional após correção runtime-safe;
- detalhe de ativo parcialmente implementado;
- eventos corporativos complexos ainda podem exigir reconciliação antes da promoção.

## Dívidas não bloqueantes por padrão

- #149 — TWR diário dedicado de RF/Tesouro permanece parcial; não fabricar TWR;
- #351/#90/#58 — refinamentos de UX/produto;
- #355–#359 — features futuras;
- #246/#360 — macroprojeto Metas + Analysis Engine;
- #361 — IA depois de #360/#246;
- #97 — OAuth.

Essas frentes só sobem de prioridade se bloquearem uma jornada crítica real do escopo aprovado.

## Bugs candidatos P1

- #352 — seleção de classe no lançamento, se ainda reproduzível e funcionalmente impeditiva;
- #354 — divergência de regra mínima de senha, se ainda reproduzível.

#353 é P2 por padrão.

## Ambiente local x OCI

### Local

Ambiente oficial para desenvolvimento, correção, suítes pesadas, migrations de teste e certificação financeira.

### OCI

Ambiente oficial para homologar o SHA já certificado. Não executar desenvolvimento permanente, não usar o host pequeno para suítes pesadas e não forçar readiness.

## Documentos canônicos para retomada

- `README.md`;
- `ROADMAP.md`;
- `CHANGELOG.md`;
- `docs/architecture.md`;
- `docs/USER_TEST_READINESS_GATE.md`;
- `docs/USER_VALIDATION_RUNBOOK.md`;
- `docs/BOOTSTRAP_DATA_FLOW.md`;
- `docs/deployment/oci-execution-index.md`;
- Issues #303, #226, #216, #158, #227, #284 e #293.

## Regra para histórico

Baselines antigos, SHAs históricos e checklists já superados permanecem acessíveis pelo Git e por changelogs datados, mas não devem ser tratados como instrução vigente se contradisserem este documento, as Issues rebaselined ou o HEAD atual.