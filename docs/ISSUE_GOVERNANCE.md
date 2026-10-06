# Governança de Issues — SGI v2

Atualizado em 06/10/2026.

## Objetivo

Manter uma hierarquia única para certificação, dados reais, operação, dívida técnica e evolução de produto. Issues não devem competir como fontes de verdade para o mesmo trabalho.

## Estado pós-promoção

1. #158, #269 e #227 estão fechadas;
2. a PR #362 promoveu a baseline arquitetural para `main`;
3. OCI/#284 é backlog futuro e não bloqueia o desenvolvimento atual;
4. #384 governa separadamente a autorização persistente para dados reais; sua
   fundação foi promovida pelas PRs #386 e #387, sem ativação;
5. #345 foi concluída e promovida pela PR #385; a Epic #344 segue por #346/#347.

## Classificação atual

### Gates / certificação

- #303 — certificação funcional assistida, concluida para `PORTFOLIO-TEST-READY`;
- #226 — Proventos, fechado;
- #216 — gate agregado, fechado;
- #158 — reconciliação final de promoção, fechada;
- #269 — security gate, fechada;
- #227 — decisão formal GO/NO-GO, fechada;
- #384 — readiness persistente e auditável, aberta e em implementação;
- #284 — OCI, backlog futuro.

### Hardening arquitetural

- #344 — Epic de enforcement;
- #345 concluída; #346 -> #347 — sequência recomendada;
- #365 deve preceder migration estrutural ampla de #364.

### Bugs acompanhados no primeiro GO

- #352 — seleção de classe; fechada apos validacao manual do seletor `Tipo de ativo`;
- #354 — divergência de senha; fechada após alinhamento frontend/backend, reabrir apenas com regressão comprovada.

#353 é P2 por padrão.

### Dívidas financeiras/estruturais

- #149 — TWR diário dedicado restante de Tesouro/RF; não blocker automático se indisponibilidade permanecer explícita;
- #83 — Backup/Restore administrativo;
- #272 — contração física residual de `corporate_events` e aliases relacionados.

### Evolução de produto

- #58 — detalhe global de ativo, parcialmente implementado;
- #90 — refinamento de Patrimônio;
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
backlog futuro. GOV-07 não deve ser executado.

Qualquer saneamento futuro deve localizar Issues com dependências superadas e
fechar somente com evidência ou Issue canônica substituta.

#293 permanece aberta até essa segunda passada terminar.

Baseline documental para iniciar GOV-06: `959d3edf051b37f18089936f8f142fd4d2958d43`.
