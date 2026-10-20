# Governança de Issues — SGI v2

Atualizado em 16/10/2026.

## Snapshot GitHub — 16/10/2026

- Foram localizadas 453 Issues no repositório: 23 abertas e 430 fechadas; não
  havia Pull Request aberta na consulta.
- `stable-15jun` está em `b37661921e3a8455f45c8b676b28955d6ad3d0ea`, igual ao
  `origin/stable-15jun` local. A comparação GitHub mostra o branch 7 commits à
  frente e 0 atrás de `main`, que está em
  `4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`.
- O working tree não está limpo. A inspeção inicial encontrou 15 alterações
  preexistentes e cinco itens não rastreados; esta rebaseline acrescentou
  documentação viva e ajustes de cobertura para a migration local e o scanner
  do Doctor. Não promover nem certificar esse conteúdo até formar um candidato
  reproduzível.

Issues abertas, agrupadas sem alterar o estado do GitHub:

- Gates/fatos: #149, #370, #408.
- Backup/governança/schema: #83, #272, #293.
- OCI backlog: #284.
- Providers/bootstrap: #127, #130, #253.
- UX/ativo/navegação: #58, #90, #351, #353.
- Renda Fixa/ferramentas: #355–#359.
- Metas/análise/IA/autenticação: #97, #246, #360, #361.

Consulte o GitHub ao vivo antes de fechar, reabrir ou reordenar uma Issue.

## Delta de política de provedores — B3

Por decisão do usuário em 16/10/2026, B3 é a fonte oficial prioritária para
proventos e eventos corporativos de ativos listados quando houver cobertura
estruturada. BRAPI pode complementar apenas fatos não publicados pela B3; Yahoo
é fallback explícito somente quando não houver cobertura B3 do emissor. A
mudança gera nova lacuna operacional NIKE34: carregar dividendos B3 recentes no
escopo do ativo e manter o grupamento de 2026 pendente até evidência da data
efetiva e resolução da fração. Issues #226/#216/#158 registram a estratégia
anterior e não autorizam uma carga global sob esta nova política.

## Objetivo

Manter uma hierarquia única para certificação, dados reais, operação, dívida técnica e evolução de produto. Issues não devem competir como fontes de verdade para o mesmo trabalho.

## Estado pós-promoção

1. #158, #269 e #227 estão fechadas;
2. a PR #362 promoveu a baseline arquitetural para `main`;
3. OCI/#284 é backlog futuro e não bloqueia o desenvolvimento atual;
4. #384 está concluída e governa separadamente a autorização persistente para
   dados reais; a promoção vigente certifica apenas a identidade runtime exata;
5. #344 foi concluída com todas as filhas #345–#350 fechadas e seus contratos
   promovidos para `main`.
6. PR #425 sincronizou `main` para `stable-15jun`; desde então o branch estável
   avançou 7 commits e está 0 commits atrás de `main`.
7. #365 e #364 foram fechadas em 08/10; as atualizações de dependências
   priorizadas também foram integradas.

## Classificação atual

### Gates / certificação

- #303 — certificação funcional assistida, concluida para `PORTFOLIO-TEST-READY`;
- #226 — Proventos, fechado;
- #216 — gate agregado, fechado;
- #158 — reconciliação final de promoção, fechada;
- #269 — security gate, fechada;
- #227 — decisão formal GO/NO-GO, fechada;
- #384 — readiness persistente e auditável, concluída com promoção operacional
  real e validação DB-first;
- #284 — OCI, backlog futuro.

### Hardening arquitetural

- #344 — Epic de enforcement concluída;
- #345–#350 — filhas concluídas, com gates e documentação integrados;
- #365 e #364 — fechadas em 08/10/2026; não são pendências correntes.

### Bugs acompanhados no primeiro GO

- #352 — seleção de classe; fechada apos validacao manual do seletor `Tipo de ativo`;
- #354 — divergência de senha; fechada após alinhamento frontend/backend, reabrir apenas com regressão comprovada.

#353 é P2 por padrão.

### Dívidas financeiras/estruturais

- #149 — TWR diário dedicado restante de Tesouro/RF; não blocker automático se indisponibilidade permanecer explícita;
- #83 — concluída e fechada em 17/10/2026 após ensaio HTTP integrado de backup,
  download autenticado e restore em bancos PostgreSQL descartáveis; worker
  durável e teste frontend permanecem hardening futuro documentado.
- #272 — contração física de `corporate_events` permanece bloqueada por
  consumidores ativos: troca de ticker por carteira ainda usa os campos
  históricos. Inventário estático em
  `docs/CORPORATE_EVENTS_LEGACY_COLUMN_INVENTORY.md`; sem DDL ou consulta de
  dados runtime.

### Segurança

- #408 — sanitização integrada pela PR #413 e testes complementares pela
  #419; CI aprovada. O comentário remoto da Issue registra deep scan verde e
  findings ausentes na `stable-15jun`, enquanto o corpo ainda diz que essa
  confirmação está pendente e cita a propagação para `main` como condição.
  O conector disponível não expõe execuções manuais/schedule nem alertas
  CodeQL; a evidência precisa ser reconciliada antes de encerrar a Issue.

### Evolução de produto

- #58 — detalhe global de ativo, parcialmente implementado;
- #90 — refinamento de Patrimônio;
- #353 — restauração de scroll ao navegar, bug UX P2;
- #97 — OAuth;
- #351 — UI/UX V2;
- #355 — taxonomia RF;
- #356 — paginação;
- #357 — exportação;
- #358 — adapter Área do Investidor B3;
- #359 — calculadoras;
- #246 — macroprojeto Metas + Análise;
- #360 — Analysis Engine determinístico;
- #361 — IA explicável depois de #360/#246.

### Providers / bootstrap

- #130 — BRAPI/capabilities/enriquecimento;
- #127 — configuração dinâmica de providers;
- #253 — Central de Bootstrap, se ainda necessária após certificação.

## Regras

- bug reproduzível deve ter Issue pequena própria;
- macroprojeto não deve esconder bug P0/P1;
- feature futura não vira blocker sem impacto material na jornada de release;
- Issue concluída ou integralmente absorvida deve ser encerrada/rotulada de forma coerente;
- evidências certificadas devem ser reutilizadas; não repetir operação destrutiva por checklist antigo;
- documentação e Issues devem ser atualizadas no mesmo macrobloco em que a decisão muda.

## Estado da sanitização

O rebaseline pós-#362 retirou OCI do caminho crítico e preservou #284 como
backlog futuro. GOV-07 continua pendente: terminar a revisão das Issues abertas
e correlacionar o estado atual com código, testes e documentação antes de fechar
#293.

Qualquer saneamento futuro deve localizar Issues com dependências superadas e
fechar somente com evidência ou Issue canônica substituta.

#293 permanece aberta até essa correlação terminar.

## Resultado da correlação GOV-07 — 17/10/2026

Inventário GitHub ao vivo: 22 Issues abertas e nenhuma PR aberta. #83 está
fechada; os demais itens foram correlacionados ao mapa abaixo. Nenhuma Issue
aberta foi identificada como duplicada ou sem destino/documentação:

- #408: sanitização implementada; permanece aberta pela evidência CodeQL
  divergente/incompleta entre o corpo e comentário remoto, além da confirmação
  de alertas em `stable-15jun` e `main`;
- #149: TWR dedicado implementado; o regulamento B3 item 95 fixa a regra de
  elegibilidade na manhã do pagamento, mas falta prova de posição custodiada
  por carteira/conta e base tributável/IRRF por lote. Promoção de runtime é gate
  operacional separado, não requisito de desenvolvimento da Issue;
- #370: conflitos de eventos permanecem fora da projeção até evidência externa
  de liquidação fracionária de KLBN11;
- #272: contração física de schema, com inventário e janela DDL ainda exigidos;
- #127/#130/#253: evolução futura de providers, enriquecimento e interface de
  bootstrap; catálogo COTAHIST-first e engine system-bootstrap já existem;
- #58/#90/#351 e #353: detalhe/UX. #353 já tem restauração global de scroll e
  testes unitários; permanecem pendentes validação de uso desktop/mobile;
- #246/#360/#361 e #97: Metas+Análise, Analysis Engine, IA e OAuth pós-GO;
- #355-#358: taxonomia RF, paginação, exportação e import B3;
- #359: frente A da calculadora de rendimentos está implementada e implantada
  na stack de testes; quatro testes determinísticos, typecheck e build passaram.
  Revisão visual desktop/mobile segue pendente; simulador tributário de Renda
  Fixa permanece separado;
- #284: backlog OCI fora do caminho local;
- #293: governança; #353 permanece P2 e não bloqueia jornada crítica;
- #83 não faz mais parte do inventário aberto.

O mapa foi validado contra os contratos e artefatos atuais no checkout local
`stable-15jun` (`5c4ad3906475316294196a826ff140cb3e4bf950`). O conector GitHub
confirma `stable-15jun` sete commits à frente e zero atrás de `main`, mas não
retorna o SHA da ponta da branch; `git ls-remote` falhou por indisponibilidade
de rede e o SHA local ainda não foi encontrado no remoto. Portanto, a correlação
está concluída para o snapshot disponível, mas #293 permanece aberta até o
checkout documental ser publicado e a ponta remota ser reconciliada. Nenhuma
alteração de runtime ou certificação foi feita.

Baseline documental para iniciar GOV-06: `959d3edf051b37f18089936f8f142fd4d2958d43`.

## Atualizacao factual — 17/10/2026

O runtime foi consultado no Docker: backend healthy, imagem rotulada com o SHA `5c4ad3906475316294196a826ff140cb3e4bf950`, `ENVIRONMENT=production`, branch `stable-15jun`, dataset `pre-prod-backup.v3:sha256:7d97c52de9ae58ad457f3ffe25055a9963a6a0dea4c9690b8dc72f900fa7133e`, Alembic `20261016_corp_ev_effective_date` e `/ready=200` (`ready_for_real_data=true`, evento 6 persistido). A certificacao vale somente para essa identidade.

O checkout/runtime estao em `5c4ad3906475316294196a826ff140cb3e4bf950`; `origin/stable-15jun` local permanece em `b37661921e3a8455f45c8b676b28955d6ad3d0ea` (tres commits atras). O SHA remoto vivo nao foi confirmado e nenhum push foi feito. Quatro itens `.tmp-candidate-*` preexistentes foram preservados.

Issues #83, #293 e #408 foram consultadas ao vivo e permanecem abertas. A prova recente de #83 cobre backup/restore por funcoes de servico e reconciliacao estrutural em banco descartavel, mas nao autentica/audita/consulta status via API administrativa. #408 aguarda confirmacao CodeQL posterior as correcoes. GOV-07/#293 aguarda correlacao final do inventario integral. Esses status prevalecem sobre fotografias anteriores neste documento; os registros historicos permanecem preservados.

Qualquer novo SHA implantado exige novo backup v3, restore, proof, gates e dry-run vinculados a identidade nova. A promocao anterior certifica apenas `5c4ad390`.
## Estado das Issues prioritarias — 17/10/2026

- #83: concluida e fechada apos ensaio HTTP ponta a ponta em bancos PostgreSQL descartaveis; documentacao em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md`.
- #408: aberta ate confirmacao CodeQL posterior as correcoes integradas.
- #293: GOV-07 aberto; proximo bloco apos #408, sem reabrir o trabalho da #83.

Os inventarios e agrupamentos anteriores neste documento sao snapshots datados; esta secao registra a mudanca posterior confirmada no GitHub.

## Validacao da entrega #359 - 17/10/2026

A primeira frente da calculadora de rendimentos foi reconstruida na stack isolada `sgi-usertest`. Quatro testes deterministas, typecheck e build frontend passaram; rota e asset responderam HTTP 200. A revisao visual desktop/mobile permanece pendente por indisponibilidade do navegador integrado. A imagem incorpora alteracoes locais nao commitadas e serve somente para testes assistidos; nao e certificacao para dados reais. Evidencias e digests em `docs/USER_TEST_STACK.md` e `docs/TOOLS_CALCULATORS.md`.

## Bloco de inventario #355 - 17/10/2026

O inventario estatico de schema, API, formulario, CSV, valuation e consumidores
foi registrado em `docs/FIXED_INCOME_TAXONOMY_INVENTORY.md`, incluindo proposta
preliminar e revisao dos caminhos de escrita. Metadados de contrato ainda sao
serializados em `notes`; `transactions` segue como ledger canonico e a tabela
de projecao antiga foi removida irreversivelmente. A FK nullable parece
compativel se ownership/classe forem validados e criacoes legadas continuarem
suportadas. A auditoria DB-only em `sgi-usertest` encontrou zero transacoes,
portanto o proximo passo e preparar massa sintetica antes da implementacao em
banco descartavel. A auditoria remota de setembro nao e estado atual. Nenhum
dado ou runtime foi alterado neste bloco.

### Atualizacao da Issue #355 - 18/10/2026

A anotacao de 17/10 acima e um snapshot historico: desde entao, metadados
estruturados, FK opcional, API/writer, formulario e CSV foram implementados.
Novos registros de Renda Fixa associam os metadados no writer canonico e
reutilizam automaticamente contrato equivalente dentro da mesma carteira; nao
ha escolha de ID interno na jornada normal. A equivalencia normaliza espacos e
caixa de nome/emissor e preserva igualdade exata dos outros termos. Os 13
testes focados passaram; o banco `sgi-usertest` permaneceu vazio. O teste
Vitest de prefill nao concluiu e validacao visual desktop/mobile segue pendente.

O corpo remoto da #355 ainda contem o criterio antigo de seletor explicito.
Antes de fechar a Issue, atualizar esse criterio para associacao transparente,
marcar os criterios demonstrados e deixar a validacao visual como pendencia. O
tracker remoto nao foi alterado porque este bloco priorizou a implementacao e
alinhamento local; nenhuma conclusao remota foi publicada.
