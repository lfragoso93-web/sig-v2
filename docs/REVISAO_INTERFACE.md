# Revisao geral da interface

Issue relacionada: #103

## Status

Baseline visual concluido em 06/07/2026.

A revisao geral foi realizada em blocos pequenos, com validacao visual ao longo das PRs #104, #105, #106, #107 e #108.

O sistema entra agora em uma pausa curta de desenvolvimento funcional, mantendo este documento como referencia para os proximos ajustes visuais.

## Objetivo

Revisar a interface do SGI v2 para deixar o sistema mais profissional, simples, moderno e confortavel em diferentes tamanhos de tela.

A revisao reduziu a sensacao de elementos apertados, melhorou a leitura das paginas principais e consolidou uma base visual mais consistente para os proximos modulos.

## Baseline definido

O padrao visual aprovado prioriza:

1. **Mais respiro interno** em cards, formularios e secoes.
2. **Largura controlada** para evitar telas muito densas em desktop e ultrawide.
3. **Hierarquia clara** entre titulo, subtitulo, conteudo e acoes.
4. **Menor densidade visual** em tabelas, filtros e blocos de dados.
5. **Responsividade real** em desktop, tablet, mobile e ultrawide.
6. **Consistencia** entre telas internas e telas de entrada.

## Telas revisadas

- Resumo.
- Patrimonio.
- Proventos.
- Transacoes.
- Rentabilidade.
- Configuracoes.
- Login.
- Registro.
- Recuperar Senha.

## Entregas principais

### Layout e componentes

- Cards, KPIs, filtros e headers de secao padronizados.
- Tabelas com mais respiro horizontal.
- Grids mais fluidos por breakpoint.
- Ajustes para telas pequenas, grandes e ultrawide.

### Resumo

- KPIs alinhados ao comportamento da pagina Patrimonio.
- Variação atual separada de rentabilidade total.
- Dropdown de ativos corrigido para nao ficar preso ao recorte da tabela.
- Filtros e grafico com comportamento mais responsivo.

### Proventos

- Cards, filtros e area Por Ativo refinados.
- Historico mensal e tabela de eventos com mais respiro.
- Layout fluido com melhor uso de largura disponivel.
- Paginacao adicionada na listagem.

### Patrimonio

- Consolidacao simplificada.
- Posições removidas da pagina para evitar redundancia com Resumo.
- Layout visual menos carregado.

### Rentabilidade

- Blocos Por Classe e Por Ativo reorganizados.
- Tabela e cards mais escaneaveis.

### Transacoes

- Busca ajustada para evitar sobreposicao do icone.
- Cards e tabela com densidade reduzida.

### Configuracoes

- Abas, cards, formularios e lista de carteiras responsivos.
- Melhor comportamento em mobile e tablet.

### Telas de entrada

- Login, Registro e Recuperar Senha unificados visualmente.
- Este padrao passa a ser referencia para novas telas.

## Criterios para proximos ajustes

- Manter commits pequenos.
- Continuar usando a branch `stable-15jun`.
- Validar visualmente em desktop, tablet e mobile.
- Evitar grandes reescritas visuais sem validacao intermediaria.
- Preservar o padrao aprovado nas telas de entrada.

## Proximos focos sugeridos

1. Auth: Google OAuth (#97).
2. Admin: edicao de usuarios e perfil superadmin (#98).
3. Compliance de documentacao e descricoes publicas.
4. Performance de queries criticas.
5. Importacao CSV de ativos.
