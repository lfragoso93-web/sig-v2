# Revisão arquitetural completa — 23/07/2026

## Escopo e conclusão

Revisão executada na branch `stable-15jun`, sincronizada com `origin/main`
(`38ad474`, PR #197). A `main` já era ancestral da branch; a sincronização não
alterou arquivos. Foram revisados arquitetura, documentação viva, contratos
canônicos, 21 CLIs/scripts operacionais, serviços, integrações, pipelines,
migrations, estrutura DB-first, 15 Issues abertas e a PR #198.

Conclusão: o núcleo financeiro DB-first está consolidado, mas o projeto ainda
não está pronto para produção. A prontidão aproximada é **88%** considerando o
escopo da primeira produção; funcionalidades futuras não entram no percentual.
O bloqueador imediato continua sendo o ensaio reconciliado da limpeza em
PostgreSQL descartável. A limpeza da base real permanece proibida.

## Estado e arquitetura

- 619 arquivos rastreados; 382 módulos Python e 153 arquivos de frontend.
- Mais de 100 módulos de teste backend rastreados.
- Backend FastAPI/SQLAlchemy async/Alembic/PostgreSQL/Redis/APScheduler.
- Frontend React 19/TypeScript/Vite/React Query/Zustand.
- Contratos financeiros `summary.v2` e `rentabilidade.v2`.
- Contratos pré-produção: inventário v2, backup v3, cleanup-impact v2,
  export v1, cleanup-execution v1 e isolated-cleanup v1.
- DB-first aplicado a catálogo, preços, taxas, proventos e snapshots.
- 24 tabelas inventariadas: 11 preservadas, 3 exportáveis e 10 reconstruíveis.
- Backup/restauração isolada, dry-run e exportação já reconciliados.

```text
Entradas (CSV / lançamentos / provedores)
  -> catálogo e aliases canônicos
  -> transações e eventos
  -> séries persistidas (asset_prices / rate_history / proventos)
  -> valuation dedicado por classe
  -> snapshots consolidados e por classe
  -> contratos canônicos
  -> Resumo / Patrimônio / Rentabilidade / Proventos / IRPF
```

## Achados e dívida técnica

### Alta prioridade

1. A PR #198 não estava portátil no Windows: `os.open()` em diretório para
   `fsync` é recusado nessa plataforma; uma asserção também ignorava o escape
   JSON de caminhos.
2. Todos os jobs da execução CI `30034526337` falharam antes de iniciar, com
   `steps=[]` e `runner_id=0`. A annotation do GitHub aponta pagamento recusado
   ou limite de gastos da conta.
3. A suíte frontend tinha um mock hoisted inválido, um teste de contrato sem a
   normalização esperada e um teste de evolução acoplado ao Recharts real.
4. A #83 diverge da implementação: backup/restore administrativo existe, mas o
   restore não exige senha, não recebe upload e não registra a operação no
   `AuditLog`.
5. O serviço legado de rentabilidade ainda é dependência de produção:
   `transactions.py`, `portfolios.py` e `csv_snapshot_rebuild_service.py`
   importam sua invalidação de cache.

### Média prioridade

6. Grandes unidades: `brapi.py` (1.280 linhas), `admin.py` (825),
   `AddTransactionModal.tsx` (833), `portfolio_service.py` (776),
   `PositionTable.tsx` (765) e `irpf_service.py` (756).
7. Entradas frontend duplicadas: `main.tsx` é ativo; `App.tsx`,
   `router/index.tsx` e `components/ProtectedRoute.tsx` formam camada antiga.
   Há também reexports para Patrimônio e API.
8. `backend/app/migrations/versions/013_add_purchase_price_to_treasury.py`
   fica fora da árvore Alembic oficial e referencia `treasury_investments`, já
   removida.
9. O router de debug pode criar usuário privilegiado e redefinir senha quando
   habilitado. Apesar das proteções existentes, deve ser removido ou isolado
   antes do go-live.
10. A #192 foi confirmada: timestamps UTC naive existem em models, backup,
    eventos corporativos e processamento de ticker.
11. `backend/TESTING.md` dizia existir 21 testes e apontava dependências para o
    arquivo errado.
12. A nota de introspecção tratava como futura uma integração já concluída.
13. README/ROADMAP declaravam 43 testes verdes para #198 sem qualificar a
    plataforma; a revisão Windows encontrou cinco falhas antes da correção.

## Issues abertas

| Issue | Estado após revisão | Ação recomendada |
|---|---|---|
| #196 | Válida, parcial | Atualizar D0; manter até integração PostgreSQL, sucesso, rollback e reconciliação |
| #192 | Válida | Manter; inventário confirmou ocorrências |
| #158 | Válida, P0 e issue-mãe | Manter; limpeza real proibida antes do ensaio |
| #151 | Válida | Registrar três consumidores residuais de cache |
| #150 | Válida | Manter; IBOV persistido segue necessário |
| #149 | Válida | Manter; Tesouro/RF ainda sem TWR diário dedicado |
| #130 | Válida, parcial | Marcar inventário, cliente v2, aliases, resolução e CSV existentes |
| #129 | Válida, fundação parcial | Registrar model/serviço/processador; provider HG, admin e rollback pendentes |
| #127 | Válida | Manter; registry seguro por capacidade não existe |
| #97 | Válida | Manter; Google OAuth não implementado |
| #90 | Válida, parcial | Atualizar cards/evolução/metas existentes; revisão visual ainda pendente |
| #83 | Válida, parcial | Registrar UI/endpoints e gaps de senha, upload, auditoria, TTL e integração |
| #58 | Válida, parcial | Marcar drawer/detalhe/preços/posições; demais telas pendentes |
| #57 | Válida, parcial | Página/router existem; score e recomendações seguem pendentes |
| #56 | Válida, fortemente parcial | Marcar PDF/CSV, ano, modelo, página e auditoria; manter para regras fiscais/testes |

Não há Issue totalmente duplicada ou obsoleta. #158/#196, #129/#130 e #56/#83
têm dependência intencional. Nenhuma deve ser fechada agora; #56, #58, #83,
#90, #129 e #130 precisam ser atualizadas antes de nova decisão.

## Pull Requests

### PR #198 — `stable-15jun` para `main`

- Draft, mergeável pelo Git, mas `UNSTABLE`.
- 11 arquivos; cerca de 2.047 inserções e 57 remoções.
- Risco alto por introduzir capacidade destrutiva, ainda que isolada.
- Controles adequados: confirmação composta, alvo isolado, lock, contagens,
  DAG, transação única, rollback e artefato redigido sem sobrescrita.
- Bloqueios: CI indisponível, portabilidade encontrada na revisão e integração
  PostgreSQL real ainda pendente.
- Decisão: **não mergear** até correções, checks verdes e ensaio reconciliado.

Não existe outra PR aberta, inclusive Dependabot, infraestrutura ou
documentação. As branches Dependabot antigas foram removidas no `fetch`.

## Validações

- `git fetch --prune` e `git merge --ff-only origin/main`.
- Backend estrutural: 11/11 testes aprovados.
- PR #198 no Windows antes da correção: 38 aprovados e 5 falhos.
- Frontend: lint, typecheck e build de produção aprovados.
- Frontend antes da correção: 79 aprovados, 2 falhos e 1 suíte com erro.
- CI: causa externa de billing/spending confirmada pela annotation.

## Riscos de produção

- Limpeza real sem ensaio reconciliado: crítico.
- CI indisponível: crítico para promoção segura.
- Restore admin sem reautenticação/auditoria: alto.
- Debug administrativo habilitável: alto.
- Legado de rentabilidade reutilizável: médio-alto.
- TWR Tesouro/RF e IBOV incompletos: médio, com ausência explícita preservada.
- Timestamps naive, monólitos, duplicações e migration órfã: médio.

## Fila priorizada

| Prioridade | Item | Impacto | Dependências | Complexidade | Estimativa |
|---|---|---|---|---|---|
| P0 | Restaurar Actions e reexecutar checks | Promoção auditável | Billing/limite | Baixa externa | 0,5 dia |
| P0 | Validar portabilidade da #198 | Artefato confiável | Nenhuma | Baixa | 0,5 dia |
| P0 | Automatizar baseline/pós de preservadas | Gate do ensaio | #196/#198 | Média | 1–2 dias |
| P0 | Executar sucesso e rollback descartáveis | Último gate da limpeza | Backup v3, CI | Alta operacional | 1–2 dias |
| P0 | Endurecer/remover debug router | Segurança go-live | Decisão operacional | Média | 1 dia |
| P1 | Concluir backup/restore admin #83 | Restore seguro e auditado | AuditLog | Alta | 3–5 dias |
| P1 | Remover legado #151 | Elimina fórmulas/cache obsoletos | Extrair invalidação | Média | 2–3 dias |
| P1 | Materializar IBOV #150 | Benchmark DB-first | Pipeline mercado | Média | 2–4 dias |
| P1 | TWR Tesouro/RF #149 | Performance por classe | Históricos | Alta | 1–2 semanas |
| P1 | UTC aware #192 | Coerência temporal | Auditoria de colunas | Média | 2–4 dias |
| P2 | Regras fiscais #56 | Homologação IRPF | Eventos complexos | Alta | 1–2 semanas |
| P2 | Consolidar frontend | Menos duplicação | Testes arquitetura | Média | 2–3 dias |
| P2 | Arquivar migration órfã | Menos ambiguidade | Confirmar uso externo | Baixa | 0,5–1 dia |
| P2 | Decompor monólitos | Revisão/testabilidade | Blocos por domínio | Alta incremental | 1–2 dias/arquivo |
| P2 | Cobertura/providers #129/#130 | Qualidade das integrações | Decisão de fonte | Alta | 1–2 semanas |
| P3 | Google OAuth #97 | Onboarding | Política/segredos | Média | 3–5 dias |
| P3 | Provedores configuráveis #127 | Flexibilidade futura | Gestão de segredos | Alta | 2–3 semanas |
| P3 | UX #90, análise #57 e ativo #58 | Evolução de produto | Núcleo estável | Média/Alta | 1–3 semanas/módulo |

## Próximos marcos

1. Saneamento local e documentação desta revisão.
2. Checks locais verdes e commit pequeno.
3. Atualização das Issues parcialmente implementadas.
4. Regularização e reexecução do GitHub Actions.
5. Captura automática de preservadas.
6. Ensaio PostgreSQL descartável: sucesso e rollback.
7. Revisão e promoção da PR #198.
8. Somente com autorização separada: planejar limpeza da base real.
