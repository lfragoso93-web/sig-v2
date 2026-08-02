# Hierarquia de rotas da carteira

## Regra canônica

Funcionalidades cujo estado depende da carteira selecionada devem permanecer sob o prefixo `/carteira`.

Rotas canônicas atuais:

- `/carteira` — resumo;
- `/carteira/patrimonio` — patrimônio;
- `/carteira/rentabilidade` — rentabilidade;
- `/carteira/transacoes` — transações;
- `/carteira/proventos` — proventos;
- `/carteira/metas` — metas da carteira selecionada;
- `/carteira/irpf` — apuração e relatórios da carteira selecionada;
- `/carteira/configuracoes` — configurações da carteira.

## Compatibilidade

Os caminhos abaixo são somente aliases legados e devem usar redirect com `replace`:

- `/metas` → `/carteira/metas`;
- `/irpf` → `/carteira/irpf`.

Novos links internos, menus, breadcrumbs e testes não devem apontar para os aliases legados.

## Garantias

- IRPF e Metas compartilham o mesmo `AppLayout` e o mesmo contexto de carteira dos demais módulos.
- A Sidebar aponta diretamente para as rotas canônicas.
- O item ativo do menu acompanha a URL final sem depender de redirect.
- Favoritos e links antigos continuam funcionando temporariamente.
- Testes estruturais impedem o retorno de links internos para `/metas` e `/irpf`.

## Validação

Checkpoint de 02/08/2026:

- testes específicos de rotas: `4 passed`;
- suíte frontend: `23 test files passed`, `86 tests passed`;
- TypeScript typecheck: aprovado;
- ESLint: aprovado com zero warnings;
- build Vite de produção: aprovado.

Issue #228 concluída.
