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
- #83 — Backup/Restore administrativo; reautenticação, auditoria, status dos
  jobs, download autenticado e retenção já estão no código. Falta validar o
  ciclo de backup e restore em banco isolado.
- #272 — contração física residual de `corporate_events` e aliases relacionados.

### Segurança

- #408 — sanitização integrada pela PR #413 e testes complementares pela
  #419; CI aprovada. A última execução do deep scan precede essas correções,
  então a confirmação CodeQL permanece pendente e a Issue segue aberta.

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

Baseline documental para iniciar GOV-06: `959d3edf051b37f18089936f8f142fd4d2958d43`.
