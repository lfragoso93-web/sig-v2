# Revisao geral da interface

Issue relacionada: #103

## Objetivo

Revisar a interface do SGI v2 para deixar o sistema mais profissional, simples, moderno e confortavel em diferentes tamanhos de tela.

A revisao deve reduzir a sensacao de elementos apertados, melhorar a leitura das paginas principais e consolidar uma base visual mais consistente para os proximos modulos.

## Problemas atuais observados

- Alguns cards, filtros, botoes e tabelas ficam muito proximos entre si.
- A densidade visual varia bastante entre paginas.
- A responsividade ainda nao esta totalmente consistente em todas as telas.
- Tabelas e filtros precisam de melhor comportamento em larguras menores.
- Algumas telas ja possuem boa base visual, mas ainda falta padronizacao global.

## Principios da revisao

1. **Mais respiro visual**: aumentar espacos entre blocos, linhas e secoes importantes.
2. **Mais simplicidade**: reduzir informacao concorrente e deixar a acao principal clara.
3. **Mais consistencia**: padronizar cards, filtros, tabelas, badges, inputs, botoes e estados.
4. **Responsividade real**: garantir uso confortavel em desktop, tablet e mobile.
5. **Profissionalismo**: melhorar hierarquia, alinhamentos, escala tipografica e acabamento visual.

## Escopo inicial

### Layout base

- Revisar `AppLayout`, `Topbar`, `Sidebar` e comportamento mobile.
- Ajustar larguras, paddings e gaps globais.
- Validar altura e densidade de headers.
- Rever comportamento de menus, filtros e acoes em telas menores.

### Componentes compartilhados

- Padronizar `KpiCard`, cards de secao, filtros, botoes, inputs, badges e empty states.
- Revisar skeleton/loading e estados de erro.
- Garantir consistencia do dark theme.
- Melhorar foco, hover e areas de toque.

### Tabelas

- Revisar densidade das linhas.
- Melhorar legibilidade de colunas numericas.
- Garantir scroll horizontal quando necessario.
- Preferir cards em mobile quando a tabela ficar extensa.
- Padronizar empty state e mensagens de erro.

## Telas prioritarias

1. Resumo.
2. Patrimonio.
3. Proventos.
4. Transacoes.
5. Rentabilidade.
6. Configuracoes.
7. Login, cadastro e onboarding, se houver impacto visual relevante.

## Plano de execucao recomendado

### Etapa 1 — Auditoria visual

- Mapear inconsistencias de espacamento, responsividade e densidade.
- Registrar screenshots ou observacoes por pagina.
- Definir uma ordem de prioridade para os ajustes.

### Etapa 2 — Tokens e componentes base

- Consolidar padroes de spacing, radius, sombra, borda e tipografia.
- Revisar componentes compartilhados antes dos ajustes pagina a pagina.

### Etapa 3 — Responsividade

- Revisar breakpoints principais.
- Ajustar grids de KPIs e cards.
- Rever tabelas e filtros em telas pequenas.

### Etapa 4 — Ajustes por pagina

- Aplicar melhorias pagina a pagina em PRs pequenas.
- Validar desktop, tablet e mobile.
- Validar dark theme.

## Criterios de aceite

- Páginas principais com mais respiro e hierarquia clara.
- Componentes compartilhados consistentes entre modulos.
- Filtros, tabelas e cards usaveis em telas menores.
- Dark theme sem quebras visuais.
- PRs pequenas e isoladas para reduzir risco de regressao.

## Observacao de processo

O desenvolvimento deve continuar na branch `stable-15jun`, com commits pequenos e validacao visual por tela.