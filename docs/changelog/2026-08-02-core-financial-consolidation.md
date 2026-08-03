# 02/08/2026 — Consolidação do núcleo financeiro e navegação de carteira

## Alterado

- Rentabilidade passou a consumir leitores canônicos para resultado realizado, capital líquido aportado e proventos.
- Criado reader histórico de posição, custo e PnL por data de corte.
- Bens e Direitos do IRPF passou a usar a projeção histórica canônica.
- O relatório IRPF foi separado em serviços de posição, regras fiscais, composição/persistência e exportação.
- A implementação antiga de Bens e Direitos e o orquestrador duplicado foram removidos de `irpf_service.py`.
- IRPF e Metas passaram a usar as rotas canônicas `/carteira/irpf` e `/carteira/metas`.
- `/irpf` e `/metas` permanecem temporariamente apenas como redirects de compatibilidade.

## Qualidade

- Backend validado com `1097 passed`, `22 skipped` e zero warnings.
- Ruff e `compileall` aprovados.
- Frontend validado com 23 arquivos de teste, 86 testes, typecheck, lint e build aprovados.
- `datetime.utcnow()` foi removido do escopo identificado pela Issue #192.
- Serviços operacionais usam UTC aware e defaults ORM `timezone=False` usam UTC naive explícito.

## Arquitetura

- Projeções canônicas são a única base para posição, custo e resultado realizado.
- IRPF mantém somente semântica fiscal sobre a projeção contábil compartilhada.
- Seeds, sincronizações externas, importação real e rebuild permanecem suspensos pelo gate #227.

## Issues relacionadas

- #56 — IRPF.
- #151 — Rentabilidade legada.
- #192 — UTC e warnings, concluída.
- #227 — gate de consolidação arquitetural.
- #228 — rotas IRPF/Metas sob `/carteira`, concluída.
