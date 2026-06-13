# Roadmap de Desenvolvimento - SIG v2

Este documento organiza a evolucao do SIG v2 em sprints praticos. A ordem prioriza primeiro estabilizar a base tecnica, depois consolidar o nucleo financeiro e, por fim, expandir os modulos de produto.

## Visao Geral

O projeto ja possui uma base relevante: backend FastAPI, frontend React/Vite, Docker, autenticacao, carteiras, transacoes, resumo patrimonial, cotacoes e alguns modulos iniciados. O principal desafio atual e alinhar contratos entre backend/frontend e remover partes legadas que ficaram incompativeis com a versao atual do modelo de dados.

## Sprint 0 - Estabilizacao Inicial

**Objetivo:** fazer o sistema rodar de ponta a ponta sem quebras estruturais.

**Escopo:**
- Corrigir routers que declaram `/api/v1` internamente enquanto tambem recebem prefixo em `main.py`.
- Corrigir chamadas do frontend que usam `/api/v1` mesmo com o cliente Axios ja configurado com esse prefixo.
- Validar fluxo basico: cadastro, login, listagem de carteiras, criacao de carteira, criacao de transacao, resumo e posicoes.
- Instalar/validar dependencias locais para rodar testes backend e build frontend.
- Garantir que `docker compose up -d --build` sobe backend, frontend, banco e Redis.

**Criterios de aceite:**
- Nao existem rotas finais duplicadas como `/api/v1/api/v1/...`.
- O frontend nao faz chamadas para `/api/v1/api/v1/...`.
- Login e navegacao protegida funcionam.
- `GET /health` responde corretamente.
- Backend inicia sem erro.
- Frontend compila.

**Prioridade:** critica.

## Sprint 1 - Unificacao de Autenticacao e Frontend

**Objetivo:** eliminar duplicidade entre a arquitetura antiga e a arquitetura ativa do frontend.

**Escopo:**
- Escolher uma unica estrategia de autenticacao. Recomendacao: manter Zustand, pois ja esta no roteador ativo.
- Migrar usos de `AuthContext` para `useAuthStore`.
- Remover ou isolar `App.tsx` legado, se nao estiver mais em uso.
- Remover `ProtectedRoute` duplicado ou manter apenas a versao usada pelo roteador ativo.
- Revisar paginas antigas e novas para evitar duplicidade de tela.
- Ajustar tela de configuracoes para funcionar com a autenticacao ativa.

**Criterios de aceite:**
- Nenhuma pagina ativa depende de provider que nao esteja montado.
- Logout limpa estado e redireciona corretamente.
- Configuracoes mostra usuario logado sem erro.
- Rotas publicas e protegidas ficam previsiveis.
- Nao ha duas fontes de verdade para usuario autenticado.

**Prioridade:** critica.

## Sprint 2 - Modelo de Transacoes e Servicos Legados

**Objetivo:** alinhar todos os servicos com o modelo atual de transacoes.

**Escopo:**
- Remover ou refatorar `transaction_service.py` antigo.
- Atualizar testes que ainda usam `TransactionType`, `asset_id`, `price_brl`, `transaction_date` e `transaction_type`.
- Revisar servicos que ainda assumem transacao ligada a `Asset` por `asset_id`.
- Definir contrato final de `Transaction`: ticker, tipo de ativo, operacao, quantidade, preco, taxas, data, moeda e observacoes.
- Criar validacoes para compra/venda.
- Impedir venda maior que a posicao atual, ou registrar regra explicita caso venda descoberta seja permitida.

**Criterios de aceite:**
- Testes de transacoes passam usando o modelo atual.
- Nenhum servico ativo importa `TransactionType` inexistente.
- Nenhum endpoint ativo acessa campo inexistente em `Transaction`.
- Criacao e exclusao de transacoes atualizam corretamente o resumo.

**Prioridade:** critica.

## Sprint 3 - Padronizacao Async no Backend

**Objetivo:** evitar erros de runtime causados por mistura de `AsyncSession` e `Session`.

**Escopo:**
- Migrar routers e services ativos para `AsyncSession`.
- Corrigir usos de `db.query(...)` em endpoints que recebem `get_db`.
- Refatorar proventos, performance e sync para SQLAlchemy async.
- Remover imports e tipos sync em rotas ativas.
- Revisar background tasks que recebem sessao de banco.

**Criterios de aceite:**
- Rotas ativas usam `await db.execute(...)` ou helpers async.
- Nenhum endpoint ativo chama `db.query(...)` sobre `AsyncSession`.
- Background tasks abrem sua propria sessao.
- Testes backend cobrem ao menos carteiras, transacoes, posicoes e auth.

**Prioridade:** alta.

## Sprint 4 - Carteiras, Posicoes e Patrimonio

**Objetivo:** consolidar o nucleo patrimonial como fonte confiavel do sistema.

**Escopo:**
- Revisar calculo de preco medio ponderado.
- Garantir que vendas reduzem custo proporcional sem alterar preco medio.
- Garantir que posicoes zeradas desaparecem.
- Revisar tratamento de taxas.
- Normalizar tipos de ativo.
- Melhorar resumo: total investido, valor atual, resultado absoluto, resultado percentual e quantidade de posicoes.
- Garantir fallback visual quando cotacao nao estiver disponivel.

**Criterios de aceite:**
- Calculos de posicao possuem testes.
- Ativos sem cotacao mostram `current_price = null`, sem usar preco medio como cotacao.
- Resumo bate com as posicoes.
- Carteiras de usuarios diferentes ficam isoladas.

**Prioridade:** alta.

## Sprint 5 - Cotacoes e Integracoes de Mercado

**Objetivo:** tornar cotacoes mais robustas e previsiveis.

**Escopo:**
- Revisar integracao BRAPI para acoes, FIIs, ETFs nacionais, cripto e Tesouro.
- Revisar yfinance para stocks e ETFs internacionais.
- Criar tratamento claro para falha externa.
- Padronizar cache em memoria ou Redis.
- Criar endpoint de cotacao por ticker, se necessario.
- Registrar logs suficientes para diagnosticar falhas de API externa.
- Revisar variaveis de ambiente usadas por integracoes.

**Criterios de aceite:**
- Falha em BRAPI/yfinance nao derruba endpoint de posicoes.
- Cotacoes ausentes retornam ausentes, nao valores inventados.
- Tickers internacionais e nacionais usam provedores corretos.
- Configuracoes ausentes sao tratadas com fallback claro.

**Prioridade:** alta.

## Sprint 6 - Proventos

**Objetivo:** entregar proventos confiaveis, com modo automatico e manual.

**Escopo:**
- Corrigir backfill de proventos para funcionar com o modelo atual.
- Separar provento global do ativo e provento da carteira.
- Calcular quantidade na data-ex.
- Tratar JCP com valor liquido.
- Implementar lancamento manual de proventos.
- Exibir historico mensal, distribuicao por ativo, valores recebidos e a receber.
- Garantir idempotencia na sincronizacao.

**Criterios de aceite:**
- Sincronizar o mesmo ativo duas vezes nao duplica proventos.
- Quantidade considerada usa posicao na data-ex.
- Dashboard de proventos mostra totais coerentes.
- Usuario consegue cadastrar provento manualmente.

**Prioridade:** alta.

## Sprint 7 - Rentabilidade

**Objetivo:** calcular rentabilidade de forma util para decisao.

**Escopo:**
- Separar lucro realizado e nao realizado.
- Calcular retorno por ativo.
- Calcular retorno por classe de ativo.
- Incluir proventos no retorno total.
- Revisar tratamento de ativos internacionais.
- Definir se cambio usado sera atual, historico ou informado na compra.
- Criar tela de rentabilidade com tabela e graficos.

**Criterios de aceite:**
- Rentabilidade por ativo bate com transacoes e cotacoes.
- Carteira mostra retorno total com e sem proventos.
- Ativos vendidos continuam contribuindo para lucro realizado.
- Tela nao quebra quando cotacao esta ausente.

**Prioridade:** media-alta.

## Sprint 8 - Historico Patrimonial

**Objetivo:** evoluir o grafico de patrimonio de aportes acumulados para valor historico real.

**Escopo:**
- Criar snapshots diarios ou mensais da carteira.
- Armazenar valor investido e valor de mercado por data.
- Usar historico de precos quando disponivel.
- Permitir periodos: 6m, 12m, 24m e tudo.
- Exibir serie de patrimonio, aportes e resultado.

**Criterios de aceite:**
- Historico nao depende apenas de transacoes.
- Grafico diferencia aporte acumulado e valor de mercado.
- Periodos funcionam sem erro.
- Dados antigos continuam exibindo fallback aceitavel.

**Prioridade:** media.

## Sprint 9 - Patrimonio por Classe

**Objetivo:** transformar a area de patrimonio em modulo completo.

**Escopo:**
- Consolidar pagina de patrimonio.
- Finalizar abas de renda variavel, Tesouro Direto e renda fixa.
- Mostrar posicoes agrupadas por classe.
- Permitir abertura de modal de novo lancamento ja pre-preenchido por classe/ativo.
- Melhorar visao de alocacao.

**Criterios de aceite:**
- Aba raiz de patrimonio deixa de ser placeholder.
- Renda variavel lista ativos corretamente.
- Tesouro Direto lista titulos.
- Renda fixa tem fluxo minimo planejado ou implementado.

**Prioridade:** media.

## Sprint 10 - Renda Fixa e Tesouro Direto

**Objetivo:** dar suporte real a ativos de renda fixa.

**Escopo:**
- Modelar CDB, LCI, LCA, CRI, CRA, debenture, poupanca e outros.
- Modelar indexadores: CDI, IPCA+, Selic, prefixado e IGPM+.
- Implementar Tesouro Direto com vencimento, quantidade, preco de compra e preco atual.
- Definir regra de marcacao a mercado.
- Criar telas de cadastro e acompanhamento.

**Criterios de aceite:**
- Usuario consegue cadastrar investimento de renda fixa.
- Usuario consegue cadastrar/acompanhar Tesouro Direto.
- Resumo patrimonial considera esses ativos.
- Tipos e indexadores ficam consistentes entre backend e frontend.

**Prioridade:** media.

## Sprint 11 - Metas e Alocacao

**Objetivo:** ajudar o usuario a planejar e rebalancear a carteira.

**Escopo:**
- Implementar metas de patrimonio alvo.
- Implementar meta de aporte mensal.
- Implementar meta de renda passiva por proventos.
- Implementar alocacao ideal por classe/ativo.
- Calcular diferenca entre alocacao atual e ideal.
- Sugerir prioridades de aporte.

**Criterios de aceite:**
- Usuario cria, edita e remove metas.
- Dashboard mostra progresso.
- Tela indica classes abaixo/acima da meta.
- Sugestoes sao explicaveis e simples.

**Prioridade:** media.

## Sprint 12 - IRPF

**Objetivo:** gerar informacoes uteis para declaracao anual.

**Escopo:**
- Consolidar posicao em 31/12 por ativo.
- Gerar dados para Bens e Direitos.
- Separar rendimentos isentos, JCP e rendimentos tributaveis.
- Registrar lucro/prejuizo realizado por mes.
- Controlar prejuizos acumulados.
- Exportar relatorio anual.

**Criterios de aceite:**
- Usuario escolhe ano-base.
- Sistema gera relatorio por ativo.
- Proventos sao classificados corretamente.
- Vendas realizadas aparecem por mes.
- Exportacao fica disponivel em formato simples.

**Prioridade:** media.

## Sprint 13 - Analise da Carteira

**Objetivo:** entregar diagnosticos e insights sobre a carteira.

**Escopo:**
- Concentracao por ativo.
- Concentracao por classe.
- Concentracao por moeda.
- Evolucao de risco por alocacao.
- Ranking de maiores ganhos e perdas.
- Alertas simples: concentracao alta, ativo sem cotacao, carteira sem diversificacao.

**Criterios de aceite:**
- Tela de analise deixa de ser placeholder.
- Indicadores usam dados reais da carteira.
- Alertas sao objetivos e acionaveis.

**Prioridade:** media-baixa.

## Sprint 14 - Administracao e Operacao

**Objetivo:** melhorar gestao e manutencao do sistema.

**Escopo:**
- Revisar painel admin.
- Gerenciar usuarios.
- Gerenciar configuracoes globais.
- Visualizar estatisticas basicas.
- Proteger endpoints admin por role.
- Remover ou proteger debug routes.

**Criterios de aceite:**
- Apenas superadmin acessa admin.
- Debug routes nao ficam expostas sem segredo.
- Configuracoes globais podem ser alteradas com seguranca.

**Prioridade:** media.

## Sprint 15 - Qualidade, CI e Release

**Objetivo:** deixar o projeto pronto para evolucao continua.

**Escopo:**
- Configurar CI com testes backend.
- Configurar CI com typecheck/build frontend.
- Adicionar lint/format padronizado.
- Criar seed de desenvolvimento.
- Revisar README para refletir o estado real.
- Criar checklist de release.
- Criar backup/exportacao basica do banco.

**Criterios de aceite:**
- PRs rodam validacoes automaticas.
- README nao promete modulos inexistentes.
- Novo desenvolvedor consegue subir o projeto seguindo a documentacao.
- Existe rotina clara de deploy/backup.

**Prioridade:** alta apos estabilizacao inicial.

## Backlog Futuro

Itens importantes, mas recomendados para depois da base estar estavel:

- Importacao de notas de corretagem.
- Importacao via extratos B3.
- Integracao com corretoras.
- Alertas por e-mail ou notificacao.
- Multi-moeda com cambio historico completo.
- Exportacao para Excel.
- Dashboard comparando carteira com CDI, IPCA, Ibovespa e S&P 500.
- Rebalanceamento automatico sugerido.
- App mobile ou PWA refinado.

## Ordem Recomendada de Execucao

1. Sprint 0 - Estabilizacao Inicial
2. Sprint 1 - Unificacao de Autenticacao e Frontend
3. Sprint 2 - Modelo de Transacoes e Servicos Legados
4. Sprint 3 - Padronizacao Async no Backend
5. Sprint 4 - Carteiras, Posicoes e Patrimonio
6. Sprint 5 - Cotacoes e Integracoes de Mercado
7. Sprint 6 - Proventos
8. Sprint 7 - Rentabilidade
9. Sprint 8 - Historico Patrimonial
10. Sprint 9 - Patrimonio por Classe
11. Sprint 10 - Renda Fixa e Tesouro Direto
12. Sprint 11 - Metas e Alocacao
13. Sprint 12 - IRPF
14. Sprint 13 - Analise da Carteira
15. Sprint 14 - Administracao e Operacao
16. Sprint 15 - Qualidade, CI e Release

## Definicao de Pronto

Uma sprint so deve ser considerada concluida quando:

- O fluxo principal da sprint funciona no navegador ou via API.
- O backend inicia sem erros.
- O frontend compila.
- Ha pelo menos testes ou validacoes manuais documentadas para o comportamento central.
- Nao foram introduzidas rotas duplicadas, chamadas duplicadas de prefixo ou contratos divergentes.
- O README ou este roadmap foi atualizado se houver mudanca relevante de escopo.
