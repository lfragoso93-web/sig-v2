# Hierarquia de rotas da carteira

Os módulos que dependem da carteira selecionada devem permanecer sob o namespace `/carteira`.

## Rotas canônicas

- `/carteira`
- `/carteira/patrimonio`
- `/carteira/rentabilidade`
- `/carteira/transacoes`
- `/carteira/proventos`
- `/carteira/metas`
- `/carteira/irpf`
- `/carteira/configuracoes`

## Compatibilidade

As rotas `/metas` e `/irpf` existem apenas como redirects temporários com `replace` para preservar favoritos e links antigos.

Novos links internos, itens de menu e testes não devem apontar para essas URLs legadas.
