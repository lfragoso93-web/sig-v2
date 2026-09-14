# Checklist executavel — promotion reconciliation #158

## Objetivo

Executar a menor reconciliation necessaria para preparar o SHA/dataset candidato
ao primeiro GO, consumindo evidencias ja certificadas e sem repetir operacoes
destrutivas por checklist historico.

## Baseline obrigatorio

Antes de qualquer comando operacional:

1. `git fetch origin`;
2. `git switch stable-15jun`;
3. `git pull --ff-only origin stable-15jun`;
4. registrar branch, HEAD local, `origin/stable-15jun`, working tree e diff para
   `origin/main`;
5. confirmar que #303, #226 e #216 estao fechadas;
6. confirmar que #158 contem o SHA/dataset alvo do bloco;
7. manter `ready_for_real_data=false`.

## Evidencias consumidas

- #303: `PORTFOLIO-TEST-READY` aprovado.
- #226: Proventos portfolio-scoped/idempotente aceito como suficiente para
  promocao controlada.
- #216: benchmarks/cambio consolidados e gate agregado fechado.
- #363: gates tecnicos recuperados.

Nao repetir essas evidencias sem finding material novo.

## Entradas minimas

Registrar na #158 antes da execucao:

- SHA candidato;
- dataset/carteira alvo;
- janela de dados;
- artefatos existentes que serao consumidos;
- comandos exatos a executar;
- comandos explicitamente proibidos no bloco;
- criterio de sucesso;
- criterio de abort.

## Comandos permitidos por padrao

- consultas read-only de contagem, cobertura e integridade;
- importacao/rebuild estritamente necessario ao delta aprovado;
- invalidador/rebuild canonico de snapshots somente quando vinculado ao delta;
- verificacoes de restart, persistencia e idempotencia;
- testes locais dirigidos ao dominio reconciliado;
- `git diff --check`.

## Comandos proibidos sem gate explicito

- `full_market_rebuild` amplo como substituto da #158;
- seed global de Proventos sem finding material novo;
- seed global de mercado apenas para repetir evidencia historica;
- migration fisica/destrutiva sem backup, inventario e autorizacao registrados;
- contracao fisica de tabelas legadas fora de janela aprovada;
- hotfix direto na OCI;
- force push, reset destrutivo ou merge de `main` por conveniencia;
- qualquer alteracao que promova `ready_for_real_data=true`.

## Reconciliation minima

Validar e registrar:

1. lifecycle de transacoes;
2. patrimonio/resumo;
3. posicoes e custo medio;
4. snapshots consolidados e por classe;
5. rentabilidade;
6. Proventos sob demanda a partir de `asset_dividends`;
7. Tesouro;
8. Renda Fixa;
9. IRPF suportado;
10. eventos corporativos materiais ao dataset;
11. restart;
12. persistencia;
13. idempotencia;
14. provider-boundary no read path financeiro.

## Criterios de abort

Abortar o bloco e registrar Issue/finding se houver:

- divergencia monetaria nao explicada;
- ausencia convertida em zero/preco/cambio/retorno artificial;
- provider externo chamado em GET/read path financeiro;
- segunda fonte de verdade para posicao, saldo, Proventos ou eventos;
- migration drift ou Alembic/metadata drift bloqueante;
- writer paralelo de entidade canonica;
- evento corporativo material `UNRECONCILED` no dataset alvo;
- falha de restart/persistencia;
- idempotencia quebrada;
- Critical/High exploravel quando o bloco entrar no security gate.

## Evidencia minima de saida

Ao concluir o microbloco operacional, registrar na #158:

- SHA inicial e final;
- dataset e janela;
- comandos executados;
- contagens antes/depois;
- relatorio financeiro;
- resultado de restart/persistencia/idempotencia;
- testes locais e resultados reais;
- riscos e pendencias;
- decisao: aprovado, aprovado com ressalvas ou abortado.

## Proximo gate

Somente depois da #158 aprovada, executar #269 sobre exatamente o mesmo SHA
candidato.
