# Validacao assistida com usuarios - SGI v2

Issue mae: #227
Gate funcional: #303
Branch obrigatoria: `stable-15jun`

## Status atual - 08/09/2026

GO para usuarios convidados testarem jornadas assistidas com contas, carteiras e
dados ficticios/descartaveis.

NO-GO para usuarios, carteiras, CSV, seeds, snapshots ou posicoes reais. A flag
`ready_for_real_data` deve permanecer `false` ate a conclusao formal dos gates
#226, #216, #158 e #227.

Baseline operacional publicado: `59a6a9fc741d557324233065137a9c1a25d4af64`.

Carteira sintetica ja alimentada no banco local de validacao:

- usuario: `portfolio-certification-303@example.com`;
- carteira: `PORTFOLIO-TEST-READY synthetic multiclasse`;
- `user_id=14`;
- `portfolio_id=13`;
- fixture #303 com 11 transacoes, precos sinteticos, provento sintetico,
  Tesouro, Renda Fixa, cripto e matriz IRPF certificada.

## Objetivo

Validar o SGI v2 com usuarios convidados em jornadas controladas antes de
qualquer decisao `ready_for_real_data=true`.

Este runbook permite somente usuarios de teste, carteiras ficticias e dados
descartaveis. Ele nao autoriza seed real de Proventos, CSV real, carteira real,
snapshot de producao, migracao fisica ou mudanca manual de readiness.

## Estado permitido

- `test_ready=true`;
- `ready_for_real_data=false`;
- ambiente local ou lab homologado com SHA exato publicado em `stable-15jun`;
- usuarios identificados como teste, sem dados pessoais financeiros;
- carteiras e transacoes ficticias, reproduziveis ou descartaveis.

## Pre-condicoes

Antes de iniciar uma rodada com usuarios:

1. Confirmar branch `stable-15jun`.
2. Confirmar HEAD local igual a `origin/stable-15jun`.
3. Confirmar working tree limpa.
4. Registrar SHA completo, data, ambiente e responsavel pela rodada.
5. Executar gates tecnicos locais aplicaveis:
   - backend `pytest -q`;
   - frontend `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build`;
   - `app.main OK`;
   - `docker compose ps` saudavel;
   - certificacoes sinteticas #303 com `status=PASS`.
6. Confirmar `/health` com Postgres ok.
7. Confirmar que `/ready` permanece fechado enquanto `ready_for_real_data=false`.
8. Confirmar que nenhum opt-in real esta ativo sem issue autorizando:
   - `SGI_BOOTSTRAP_ENABLE_DIVIDENDS`;
   - `SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS`;
   - qualquer comando real de importacao CSV ou seed.

## Perfis de usuario

Usar no minimo tres perfis de validacao:

| Perfil | Objetivo | Dados permitidos |
| --- | --- | --- |
| Usuario iniciante | Validar onboarding, carteira vazia e navegacao basica | carteira ficticia simples |
| Usuario investidor comum | Validar multiclasse, filtros e entendimento dos cards | fixture sintetica ou transacoes ficticias |
| SuperAdmin/tester | Validar controles administrativos e bloqueios | contas de teste e ambiente descartavel |

Nenhum perfil deve usar extrato, nota, CPF, email pessoal financeiro, carteira
real ou posicao real.

## Jornadas obrigatorias

Cada usuario de teste deve executar, acompanhado por observador tecnico:

1. Cadastro ou login de conta de teste.
2. Criacao ou selecao de carteira ficticia.
3. Navegacao pelas telas:
   - Resumo;
   - Patrimonio;
   - Rentabilidade;
   - Transacoes;
   - Proventos;
   - IRPF;
   - Configuracoes.
4. Validacao de estados vazios e mensagens de indisponibilidade.
5. Cadastro manual de transacoes ficticias quando aplicavel.
6. Importacao CSV somente com arquivo sintetico aprovado.
7. Conferencia de valores esperados contra oraculo sintetico.
8. Restart controlado do backend ou Compose entre duas leituras.
9. Revalidacao visual apos restart.
10. Confirmacao de que nenhum dado real foi usado.

## Matriz de aceite

| Area | Aceite minimo |
| --- | --- |
| Autenticacao | login/cadastro de teste conclui sem erro visivel |
| Carteira | criar, selecionar e navegar sem misturar dados entre usuarios |
| Transacoes | compra, venda parcial, venda total e recompra ficticias preservam custo e realizado |
| CSV sintetico | dry-run, confirmacao, importacao e reexecucao seguem o contrato #303 |
| Patrimonio | valores batem com reconciliacao sintetica no centavo |
| Rentabilidade | indisponibilidade de classe sem cobertura aparece explicitamente |
| Proventos | direitos sao calculados sob demanda, sem materializacao por carteira |
| IRPF | valores sinteticos batem com a matriz de aceite #303 |
| Resiliencia | restart nao perde carteira, snapshots ou cache essencial |
| Admin | usuario comum nao acessa superficies SuperAdmin |

## Evidencia da rodada

Registrar internamente, sem segredos e sem dados pessoais reais:

- SHA completo;
- ambiente;
- data/hora;
- perfis testados;
- jornadas concluidas;
- bugs encontrados;
- screenshots somente se nao expuserem dados sensiveis;
- resultado final: `PASS`, `PASS_WITH_FINDINGS` ou `FAIL`.

Findings devem virar issues pequenas quando forem reproduziveis. A rodada nao
autoriza `ready_for_real_data=true` se houver blocker aberto.

## Criterios para avancar aos gates reais

A validacao assistida com usuarios ficticios permite seguir para a cadeia real
somente quando:

- todas as jornadas obrigatorias forem `PASS` ou findings nao bloqueantes;
- backend, frontend e Docker local estiverem verdes no mesmo SHA;
- #303 tiver evidencia sintetica suficiente;
- nao houver bug P0/P1 aberto afetando onboarding, transacoes, CSV, patrimonio,
  rentabilidade, Proventos ou IRPF;
- documentacao viva estiver sincronizada.

Depois disso, a ordem permanece:

1. #226 - duas execucoes reais controladas de Proventos;
2. #216 - reconciliacao do gate agregado;
3. #158 - importacao/rebuild/reconciliacao operacional;
4. #227 - decisao formal GO/NO-GO;
5. somente entao avaliar `ready_for_real_data=true`.

## Criterios de bloqueio

Interromper a rodada e manter `ready_for_real_data=false` se ocorrer:

- uso acidental de dado real;
- provider chamado por GET ou calculo financeiro comum;
- divergencia financeira sem explicacao;
- perda de dados apos restart;
- usuario acessando carteira de outro usuario;
- SuperAdmin exposto a usuario comum;
- importacao CSV real ou seed real fora da issue autorizadora.
