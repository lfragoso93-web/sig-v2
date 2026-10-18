# Roadmap - SGI v2

> Ultima atualizacao: 18/10/2026.

## Proximo bloco ativo - fechar experiencia de Renda Fixa e priorizar ferramentas

- O ambiente unico de validacao assistida e o Compose `sig-v2`, publicado pelo Cloudflare Tunnel. Toda alteracao destinada aos usuarios deve ser publicada nessa imagem; nao usar `sgi-usertest`.
- #355 tem contratos estruturados, associacao por termos equivalentes, prefill de Resumo/Tesouro e fluxos CSV. A rodada atual remove a escolha manual de tratamento fiscal e o campo separado de emissor; liquidez diaria oculta e limpa carencia.
- #359 compara titulos por tipo de produto. O tratamento fiscal vem automaticamente da taxonomia; premissas, fontes e limites estao em `docs/TOOLS_CALCULATORS.md`.
- Testes focados da rodada: frontend 31/31, backend de contratos 20/20, typecheck e build de producao aprovados. Commit publicado e imagens aplicadas em `sig-v2`.
- A validacao visual desktop/mobile e acessibilidade segue pendente de uma sessao de navegador disponivel. Readiness/certificacao de dados reais nao e gate para esta validacao assistida, conforme decisao do usuario.

## Estado publicado do ambiente — 18/10/2026

- Branch `stable-15jun`; commit de produto `8391474917684caa4e92f30d8b7c00cdb7ac5a28` publicado no remoto e aplicado na stack `sig-v2`. Digests e checagens em `docs/DEVELOPMENT_CONTINUITY.md`.
- Backend e frontend atuais foram aplicados ao projeto Compose existente
  `sig-v2`; banco, Redis e volumes foram preservados. Evidência e digests estão
  em `docs/DEVELOPMENT_CONTINUITY.md`.
- Alembic está em `20261017_fixed_income_contracts`; `/health=200`, endpoints
  de contratos/CSV aparecem na API e a URL pública e seu bundle responderam 200
  na última validação registrada.
- `/ready=503` decorre da divergência entre o SHA/revisão/dataset atuais e o
  evento de certificação anterior. Nenhuma nova certificação foi promovida.
- O navegador integrado não está disponível nesta sessão; a verificação visual
  desktop/mobile permanece pendente. Testes focados do comparador: 15/15;
  typecheck e build de produção passaram após a correção para rejeitar campos
  vazios.

As seções abaixo descrevem fases e snapshots históricos; não são o status
operacional vigente quando divergirem deste bloco.

## Estado histórico do projeto

O SGI v2 está em fase de **pós-GO e hardening arquitetural**, com a baseline
funcional promovida para `main` pela PR #362 e o núcleo DB-first consolidado.
Na sequência, a PR #425 sincronizou `main` em `stable-15jun`. O branch estável
avançou desde então e, na comparação GitHub de 16/10, estava 7 commits à frente
e 0 atrás de `main` (`4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`). O HEAD publicado
é `b37661921e3a8455f45c8b676b28955d6ad3d0ea`.

Estado histórico da identidade runtime certificada em 06/10/2026; não aplicar
ao runtime observado em 16/10/2026:

```text
GO_ASSISTED=true
ready_for_real_data=true
/health=200
/ready=200
```

Na validação de 17/10, as imagens candidatas backend/frontend estavam
implantadas, o head Alembic era `20261016_corp_ev_effective_date`, `/health=200`
e `user_test_readiness` retornou `GO_ASSISTED`, sem blockers/warnings e com zero
escritas. `/ready=503` por divergência do evento persistido anterior. Backup v3
pós-migration, restore isolado e dry-run #384 passaram; o plano aguarda
autorização explícita de execução. O mapa operacional está em
`docs/DEVELOPMENT_BASELINE_2026-10-16.md`.

Branch obrigatória: `stable-15jun`.

## Próximo ciclo de desenvolvimento e testes — governante

1. Atualizar esta documentação factual e criar o novo SHA; cada mudança de SHA
   invalida o plano #384 atual e exige novo backup v3, restore, proof e dry-run.
2. Reconciliar as evidências remotas divergentes da #408: obter o resultado do
   deep scan pós-#413/#419 e estado dos alertas CodeQL em `stable-15jun` e
   `main`; não repetir o workflow completo até localizar a execução existente.
   #83 foi concluída e fechada em 17/10.
3. Revisar a confirmação exata do novo dry-run #384 e executar somente após
   autorização explícita para a identidade apresentada.
4. Concluir GOV-07/#293 e escolher uma entrega de produto. #284 permanece
   backlog de OCI e não participa deste ciclo local.

Baseline operacional atual: `docs/DEVELOPMENT_BASELINE_2026-10-16.md`.

### Estado dos gates de codigo - 17/10/2026

- #408: corpo remoto e comentário remoto têm estados conflitantes sobre a
  confirmação CodeQL; conector disponível não consulta execuções manuais nem
  alertas. Issue permanece aberta até a evidência ser reconciliada.

- Backend: 2.401 testes passaram, 5 foram skipped e nenhum falhou na suite completa, executada em container isolado, com a arvore somente leitura e rede desativada.
- Flake8 e mypy passaram; o mypy analisou 411 arquivos. O Architecture Doctor passou nos 6 checks estaticos.
- O fresh migration gate aplicou todas as revisoes num PostgreSQL 16 descartavel e o drift gate passou; head local: `20261016_corp_ev_effective_date`.
- Frontend: 171 testes, typecheck e lint passaram na validacao de 16/10.
- O checkout continua sem SHA candidato reproduzivel por conter alteracoes locais. A imagem e a certificacao ainda nao foram atualizadas. O proximo passo exige revisar/consolidar o candidato, resolver CodeQL #408 e cumprir backup/restore isolado #83.

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

As Issues #365 e #364 foram fechadas em 08/10/2026. Os upgrades de dependências
priorizados também foram integrados. A próxima fronteira é confirmar a correção
de segurança #408 com CodeQL, fechar o escopo residual da #83 em banco isolado,
concluir a correlação GOV-07 da #293 e então escolher uma única entrega de
produto.

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

O SHA `3ab054f61e34f440dddf93c170259958243d58af` acima é a identidade histórica
promovida em 06/10/2026. O checkout estável atual é
`b37661921e3a8455f45c8b676b28955d6ad3d0ea`, mas o working tree está modificado.
O runtime observado não corresponde à identidade certificada e `/ready` está
fechado. Não inferir certificação para o checkout atual sem um ciclo novo.

## Rebaseline de segurança e continuidade — 16/10/2026

- #408: sanitização em `stable-15jun` pela PR #413; regressões
  complementares integradas pela #419 com CI aprovada. A última execução do
  deep scan é anterior às correções; confirmação CodeQL continua pendente.
- #83: código estável já inclui download autenticado, reautenticação de restore,
  auditoria, status persistido e retenção. Falta um ciclo de integração em banco
  descartável; nenhum restore real foi executado.
- #293: GOV-07 continua pendente até concluir a revisão de Issues abertas e
  sincronizar os documentos vivos.
- Inventário GitHub: 23 Issues abertas, nenhuma PR aberta; ver
  `docs/ISSUE_GOVERNANCE.md` para agrupamento e sequência.
- Não há PRs abertas no inventário consultado. OCI/#284 permanece backlog.

## Dívidas financeiras não bloqueantes por padrão

### #149 — TWR diário Tesouro/Renda Fixa

- Tesouro: valuation DB-first, snapshots dedicados, calendário canônico e
  eventos monetários persistidos consumidos uma única vez no TWR;
- Renda Fixa: lifecycle, valuation e TWR dedicados, com oracles para aportes,
  resgates parciais, múltiplas aplicações e fronteiras de cobertura;
- cadeia temporal: lacunas de PU, benchmark ou calendário permanecem explícitas
  e não promovem retorno parcial como oficial;
- elegibilidade: regra oficial B3 item 95 encontrada — título disponível na
  conta de custódia na manhã do pagamento antes de depósitos/transferências;
- pendência factual: posição de custódia por conta/carteira nessa manhã e base
  tributável/IRRF por lote; CSV agregado não prova esses valores;
- certificação de runtime é gate separado para promoção a dados reais, não
  requisito de cada iteração de desenvolvimento da #149.

Não fabricar retorno nem evento monetário. Indisponibilidade e cobertura
incompleta devem continuar explícitas.

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
| Tesouro | 🟢 valuation/TWR dedicados; ingestão factual de cupons/amortizações pendente na #149 |
| Renda Fixa atual | 🟢 lifecycle, valuation e TWR dedicados |
| RF TWR diário | 🟢 oracles canônicos; nova identidade runtime ainda exige certificação |
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

## Atualizacao factual — 17/10/2026

O runtime foi consultado no Docker: backend healthy, imagem rotulada com o SHA `5c4ad3906475316294196a826ff140cb3e4bf950`, `ENVIRONMENT=production`, branch `stable-15jun`, dataset `pre-prod-backup.v3:sha256:7d97c52de9ae58ad457f3ffe25055a9963a6a0dea4c9690b8dc72f900fa7133e`, Alembic `20261016_corp_ev_effective_date` e `/ready=200` (`ready_for_real_data=true`, evento 6 persistido). A certificacao vale somente para essa identidade.

O checkout/runtime estao em `5c4ad3906475316294196a826ff140cb3e4bf950`; `origin/stable-15jun` local permanece em `b37661921e3a8455f45c8b676b28955d6ad3d0ea` (tres commits atras). O SHA remoto vivo nao foi confirmado e nenhum push foi feito. Quatro itens `.tmp-candidate-*` preexistentes foram preservados.

Issues #83, #293 e #408 foram consultadas ao vivo e permanecem abertas. A prova recente de #83 cobre backup/restore por funcoes de servico e reconciliacao estrutural em banco descartavel, mas nao autentica/audita/consulta status via API administrativa. #408 aguarda confirmacao CodeQL posterior as correcoes. GOV-07/#293 aguarda correlacao final do inventario integral. Esses status prevalecem sobre fotografias anteriores neste documento; os registros historicos permanecem preservados.

Qualquer novo SHA implantado exige novo backup v3, restore, proof, gates e dry-run vinculados a identidade nova. A promocao anterior certifica apenas `5c4ad390`.
## Resultado GOV-07 — 17/10/2026

Consulta ao vivo encontrou 22 Issues abertas, sem PR aberta. A correlacao nao
identificou Issue claramente duplicada ou sem destino; #83 esta fechada, #353
ja tem implementacao e testes unitarios com validacao desktop/mobile restante,
e os outros residuos estao classificados em `docs/ISSUE_GOVERNANCE.md`. A
correlacao esta concluida para o snapshot local, mas #293 segue aberta enquanto
nao for possivel reconciliar/publicar o snapshot: o conector nao forneceu o SHA
da ponta `stable-15jun`, e a consulta Git falhou por rede. Nenhuma imagem ou
runtime foi alterado neste bloco.

## Atualizacao de execucao — 17/10/2026

A Issue #83 foi fechada como concluida apos backup, download autenticado e restore via API em ambiente PostgreSQL descartavel; o runbook e a evidencia estao registrados em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md` e `artifacts/admin-backup-restore/20261017-issue83/`. Proximo bloco: confirmar CodeQL para #408; depois concluir GOV-07/#293. As etapas antigas que listavam #83 como pendente sao fotografias anteriores a esta execucao.


## Atualizacao #355 - validacao do bloco backend - 17/10/2026

A stack `sgi-usertest` foi reconstruida com backend e frontend. Migration
`20261017_fixed_income_contracts` aplicada automaticamente no alvo `head`
configurado somente na stack de testes. Os 18 testes focados passaram; teste
PostgreSQL transacional rejeitou FK cross-portfolio e confirmou rollback sem
linhas residuais. `/health=200`, API presente na OpenAPI e frontend em
`127.0.0.1:18080=200`. `/ready=503` segue esperado para identidade `testing`
sem dataset/certificacao reais. A interface ainda nao cadastra/associa contratos;
proximo passo funcional e integrar formulario de aplicacao/resgate com a API,
mais cenarios de edicao/importacao legado. Digests no runbook de testes.


## Atualizacao de execucao — Issue #355 — 17/10/2026

- **Concluido neste bloco:** formulario de transacoes integrado a API de contratos estruturados; criacao/associacao atomica e edicao com preservacao do vinculo e dos valores originais.
- **Compatibilidade:** contratos sao opcionais para lancamentos legados; CSV antigo continua funcionando sem associacao inferida. CSV estruturado (colunas explicitas de contrato e exportacao) permanece pendente.
- **Validacao:** 16 testes focados de frontend, typecheck e quatro testes backend passaram. `sgi-usertest` usa a migration `20261017_fixed_income_contracts`; backend/frontend saudaveis; `/ready=503` esperado para ambiente sintetico sem certificacao real.
- **Proximo bloco:** desenhar e implementar importacao/exportacao CSV com campos de contrato explicitos, preservando dry-run, validacao e compatibilidade do formato antigo.


## Atualizacao de execucao - CSV de Renda Fixa - 18/10/2026

- **Concluido:** template, importacao dry-run/atomica e exportacao de transacoes agora carregam metadados de contratos estruturados.
- **Agrupamento:** `fixed_income_contract_key` e local ao arquivo. Linhas com a mesma chave e metadados coerentes criam/reutilizam um contrato na carteira importada; IDs internos nao sao exportados.
- **Compatibilidade:** arquivo antigo com nove colunas permanece valido e nao cria contrato nem infere vinculo. Metadados de contrato fora de `RENDA_FIXA`, chaves sem metadados ou termos divergentes sao bloqueados no dry-run.
- **Validacao:** 82 testes backend, 7 testes frontend, typecheck e build Docker passaram. As imagens atuais estao aplicadas a `sgi-usertest`; `/ready=503` continua esperado para identidade sintetica. O primeiro build combinado retornou EOF apos a exportacao; o backend foi reconstruido em comando isolado e validado no runtime.
- **Proximo passo:** exercitar o fluxo visual com arquivo sintetico e conferir a experiencia de exportacao/download em desktop e mobile antes de fechar a Issue #355; nenhum CSV real esta autorizado por esta etapa.


## Atualizacao de execucao - Hierarquia do formulario RF - 18/10/2026

- **Concluido:** tipo de produto aparece antes do indexador na criacao de contrato de Renda Fixa.
- **Metadado fiscal:** produtos com tratamento usualmente isento sugerem `tax_exempt=true`; os demais iniciam como nao informado. A escolha manual e preservada ao trocar o produto. A sugestao nao calcula IRPF nem substitui conferencia documental.
- **Validacao:** 14 testes focados do modal, `npm run typecheck` e build Docker passaram. Frontend atualizado na stack isolada `sgi-usertest`; API `/health=200`, frontend `127.0.0.1:18080=200`; `/ready=503` esperado em testing sem certificacao real.
- **Proximo bloco:** validar visualmente os fluxos de cadastro e CSV com dados sinteticos, em desktop e mobile, sem inserir dados financeiros reais.


## Atualizacao de execucao - Agrupamento automatico RF e prefill Tesouro - 18/10/2026

- **Implementado no checkout:** reutilizacao de contrato com termos integralmente equivalentes na mesma carteira; o formulario deixa de mostrar a escolha de ID/registro. Atalho de Renda Fixa no resumo hidrata o contrato apenas quando existe uma correspondencia unica. Atalho do Tesouro passa vencimento conhecido e usa catalogo/cotacao persistida para os demais termos disponiveis.
- **Validacao:** typecheck passou. Build frontend compilou. Nao foram adicionados nem executados testes neste bloco.
- **Runtime:** BuildKit encerrou com EOF ao exportar a imagem backend; depois Docker Desktop informou falha de inicializacao WSL (`0xc00000fd`). Imagens e estado dos containers nao confirmados como aplicados.
- **Retomada:** recuperar Docker, auditar estado da stack `sgi-usertest`, concluir build/recreate e verificar as rotas antes da validacao visual. Dados/volumes da stack principal nao foram alvo.

### Recuperacao confirmada - 18/10/2026

Docker voltou sem reinicio do engine; rebuild e recreate backend/frontend concluidos. `/health=200`, frontend 200, migration `20261017_fixed_income_contracts (head)`, `/ready=503` esperado para testing sintético. Imagens em execucao e digests estao em `docs/USER_TEST_STACK.md`; dados e volumes preservados. Proximo bloco: validacao visual/funcional dos atalhos e agrupamento automatico usando somente dados sinteticos.

### Validacao automatica - agrupamento RF e prefill - 18/10/2026

- Teste backend de regressao adicionado: writer reusa contrato equivalente na mesma carteira e separa termos divergentes. Suite `test_fixed_income_contract_service.py`: 12 passaram (SQLite em memoria).
- Teste frontend de prefill foi adicionado; Vitest nao concluiu, mesmo apos elevacao, e foi interrompido sem resultado. `npx tsc --noEmit` passou.
- Browser integrado indisponivel (`agent.browsers.list()` vazio); fluxo desktop/mobile segue pendente de validacao visual em sessao de navegador.
- Imagem atualizada e aplicada em `sgi-usertest`; digests e estado abaixo em `docs/USER_TEST_STACK.md`. Backend healthy, `/health=200` dentro do container, frontend `127.0.0.1:18080=200`; `/ready=503` esperado para ambiente sintetico. DB, Redis e volumes preservados.
- Proximo passo: completar exercicio visual/funcional dos atalhos e criar/importar contratos somente com dados sinteticos quando houver browser disponivel.

### Escopo por carteira do agrupamento automatico - 18/10/2026

A regressao agora cobre isolamento entre carteiras: dois contratos equivalentes em carteiras distintas recebem IDs distintos. Suite backend do servico: 13 testes passaram em SQLite em memoria. A imagem backend foi atualizada no sgi-usertest; detalhes e identidade final em `docs/USER_TEST_STACK.md`. Continua pendente validacao visual por indisponibilidade do browser integrado e o teste Vitest do prefill nao concluiu.

Revisao da Issue #355 encontrou criterio remoto antigo de seletor explicito, enquanto a implementacao atual remove esse seletor e agrupa por equivalencia de termos dentro da carteira. A divergencia foi registrada para alinhamento no proximo bloco documental; nenhum estado remoto foi alterado.

O backend recomposto para este bloco esta em `sha256:700171073da7ac0fff016e3f64627f19dc0a72ff0aaf6ea90667c63d367e7708`; migration head confirmada, servicos saudaveis, zero transacoes/contratos no banco de teste e readiness 503 esperado. A validacao frontend/visual permanece pendente.

### Normalizacao da identidade textual de contrato - 18/10/2026

O schema agora colapsa espacos consecutivos em nome de exibicao e emissor; o writer compara a caixa do emissor como ja fazia para o nome. Isso evita contratos duplicados por variacao tipografica em campos textuais, mantendo os demais termos tipados exatos e o escopo da carteira. Os 13 testes focados passaram apos a mudanca. Imagem backend sera atualizada neste bloco; visual e Vitest seguem pendentes.

Digest backend final deste bloco: `sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58`; frontend preservado em `sha256:7224856e167182dab7db87f49c69a92a2ba88bb1d4d445b5eace5666d8b57169`. Ambos refletem o estado de testes local, nao uma release certificada.

Correcao do registro anterior: a frase de que a imagem backend "sera atualizada" foi superada pela atualizacao concluida. Digest backend ativo: `sha256:93053a6fb003b46b84beaea359235033deb051f4cde3654904e436aaef1cba58`; verificacao final em `docs/USER_TEST_STACK.md`.

### Stack completa para testes assistidos - 18/10/2026

Backend e frontend atuais aplicados em `sgi-usertest`. Digests, identidade, checagens e limites em `docs/USER_TEST_STACK.md`. Frontend e bundle retornam 200, rotas de contratos RF e exportacao CSV estao presentes na OpenAPI, banco/volumes permanecem preservados e sem transacoes/contratos/eventos de certificacao. Pronta para testes assistidos por usuarios; `/ready=503` e esperado e nao ha certificacao de dados reais. A verificacao visual do agente e Vitest de prefill seguem pendentes.


## Atualizacao de execucao - UX fiscal e carencia de Renda Fixa - 18/10/2026

- O tipo de produto determina `tax_exempt` tanto no frontend quanto no schema da API. CDB, RDB, LC, debenture comum, Letra Financeira e Outro seguem tabela regressiva. LCI, LCA, LIG, CRI, CRA e debenture incentivada sao classificados como isentos, condicionados aos requisitos legais da emissao e do titular.
- O nome do titulo passa a incluir o emissor; o campo separado foi removido. Contratos legados continuam preservados e o agrupamento considera o nome de exibicao informado.
- Liquidez diaria limpa vencimento/carencia; carencia fica oculta e o payload envia `grace_period_end=null`.
- O simulador #359 escolhe o tipo de cada titulo e deriva a aliquota sem perguntar ao usuario se o produto e isento.
- Testes: frontend 31/31; backend `test_fixed_income_contract_service.py` 20/20; `npm run typecheck` aprovado. Imagens atualizadas e publicadas em `sig-v2` no commit `8391474917684caa4e92f30d8b7c00cdb7ac5a28`; `/health=200`, rota/bundle publicos 200 e Alembic head. `/ready=503` continua associado a identidade de certificacao anterior; nenhum evento foi promovido. DB, Redis, volumes e Tunnel preservados.
- Limite: classificacao por tipo nao transmite a declaracao IRPF nem substitui informe financeiro; isencoes dependem do enquadramento legal. Validacao visual depende de browser conectado.
