# Governança de Issues — SGI v2

Atualizado em 10/09/2026.

## Objetivo

Manter uma hierarquia única para certificação, dados reais, operação, dívida técnica e evolução de produto. Issues não devem competir como fontes de verdade para o mesmo trabalho.

## Cadeia de promoção para dados reais

1. #303 — fechar `PORTFOLIO-TEST-READY` e congelar SHA candidato;
2. #226 — fechar estratégia operacional de Proventos;
3. #216 — fechar gate agregado de seeds/bootstrap;
4. #158 — executar `promotion reconciliation` sobre SHA/dataset congelados;
5. #284 — homologar exatamente o mesmo SHA na OCI;
6. #227 — emitir GO/NO-GO amplo;
7. somente depois avaliar `ready_for_real_data=true` e promoção para `main`.

## Classificação atual

### Gates / certificação

- #303 — certificação funcional assistida;
- #226 — Proventos;
- #216 — gate agregado;
- #158 — reconciliação final de promoção;
- #284 — homologação OCI;
- #227 — decisão formal GO/NO-GO.

### Bugs candidatos a blocker do primeiro GO

- #352 — seleção de classe; P1 se ainda funcionalmente impeditiva;
- #354 — divergência de senha; P1 se ainda reproduzível.

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

GOV-01..05 concluíram o rebaseline de readiness, gates reais, OCI, backlog funcional e documentação raiz. A próxima etapa é **GOV-06 — sanitização final de Issues**.

GOV-06 deve localizar Issues abertas que descrevem trabalho já concluído, duplicidades/overlaps residuais e trackers com dependências superadas. Fechar somente com evidência ou Issue canônica substituta, preservando histórico útil antes do encerramento.

#293 permanece aberta até essa segunda passada terminar.

Baseline documental para iniciar GOV-06: `db2c612dcf0e3a7b27bcebf9dc18b3b5d38e1691`.