# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — validação pré-merge da Fase 3 (20/07/2026)

- Componentes frontend órfãos que ainda importavam o hook legado `usePerformance.ts` foram removidos.
- O typecheck global deixa de depender de tipos pertencentes a um cliente já eliminado.
- A remoção preserva os consumidores canônicos atuais: Resumo usa `usePortfolio`, Rentabilidade usa `useRentabilidade` e Patrimônio usa snapshots via `useEvolution`.
- Nenhum cálculo financeiro foi recriado no frontend e nenhum workflow foi solicitado manualmente.

### Concluído — Fase 3 Patrimônio (20/07/2026)

- Evolução consolidada e por classe passou a consumir exclusivamente `PortfolioSnapshot` e `PortfolioClassSnapshot`.
- Períodos de 6, 12 e 24 meses usam fronteiras determinísticas de meses-calendário; todo o histórico permanece sem corte artificial.
- Estados de loading, erro com retry, vazio, aguardando backfill e classe sem motor dedicado são distintos.
- Seletor de classes e catálogo de rótulos foram centralizados e compartilhados.
- Tooltips diário e mensal apresentam patrimônio, custo, resultados, TWR, fonte, cobertura parcial e estimativa diretamente dos contratos canônicos.
- Reconciliação consolidado × classes é avaliada apenas na mesma `snapshot_date`.
- Reconciliação intradiária compara somente `summary.v2`, posições e distribuição materializados na mesma referência.
- O frontend valida estritamente os dois contratos e não recalcula diferenças financeiras.
- Clientes órfãos `portfolioService.ts` e `usePerformance.ts`, incluindo referências a `/patrimonio-history` e `/equity-history`, foram removidos.
- Contratos Pydantic estritos foram adicionados aos seis endpoints de leitura patrimonial.
- Validação local disponível: 68 testes frontend aprovados, typecheck focado de Patrimônio e compilação Python aprovados.
- Nenhum workflow remoto foi disparado, preservando a cota da conta gratuita.
- TWR de Tesouro Direto e Renda Fixa permanece explicitamente fora do escopo e segue na Issue #149.
- Dependências #146, #138, #137 e #133 não foram alteradas.


### Concluído — Fase 2 Proventos (19/07/2026)

- Pipeline DB-first consolidado entre evento global, direito materializado da carteira e reconhecimento pela data de pagamento.
- Coleta diária baseada no catálogo global de ativos elegíveis, sem limitar a descoberta à posição atual da carteira.
- Leitura da página separada de materialização e cálculo de elegibilidade centralizado pela data de corte.
- Contratos Pydantic e TypeScript estritos para KPIs, lista, histórico mensal e distribuição.
- Filtros de ano, status, classe e tipo compartilhados por todos os componentes.
- Serviço FII paralelo, cliente batch e rotas administrativas residuais removidos após auditoria de consumidores.
- Dividendos, JCP, rendimentos, amortizações, bonificações e subscrições normalizados e cobertos por testes.
- Seed, coleta, materialização, rastreabilidade e idempotência validados para ações, FIIs, ETFs nacionais e BDRs.
- Eventos não monetários excluídos dos agregados financeiros pelo contrato canônico `is_cash`.
- Histórico mensal ampliado com composição reconciliada por classe em uma única consulta.
- Popover mensal acessível por hover, foco, teclado e toque, renderizado em portal e ajustado à viewport.
- Frontend passou a diferenciar loading, erro e vazio sem converter ausência ou falha em zero.
- Validação final local: 78 testes backend e 48 testes frontend aprovados, além do typecheck TypeScript.
- Migração destrutiva dos campos legados permanece reservada ao rebuild controlado da Issue #158.
- Dependências #146, #138, #137 e #133 não foram alteradas.


### Planejamento — Fase 2 Proventos (18/07/2026)

- Página Resumo concluída e promovida para a `main` pela PR #164.
- Criada a Issue-mãe #165 para reconstrução e validação ponta a ponta de Proventos.
- Arquitetura atual auditada, incluindo contratos temporais, filtros divergentes, escrita durante leitura, serviços paralelos e legado de modelo.
- Definida a sequência: testes de caracterização, contratos e filtros, separação de leitura/materialização, consolidação do pipeline, validação por classe e revisão do frontend.
- Issues #92 e #95 preservadas como entregas concluídas; #131 vinculada como sub-bloco posterior.
- Dependências #146, #138, #137 e #133 permanecem fora do escopo desta fase.

### Corrigido — Página Resumo (18/07/2026)

- KPIs reconciliados entre Resumo, Patrimônio e valuation canônico.
- `summary.v2` e posições validados nas fronteiras backend e frontend, sem recomposição financeira local.
- Resultado atual coberto para vendas parciais, posições encerradas e carteiras mistas.
- Cobertura completa e parcial de preços explicitada, preservando custo quando falta cotação.
- Histórico consolidado e por classe migrado para snapshots canônicos.
- Gráfico patrimonial validado com ganho acima do aplicado e perda abaixo da linha zero; issue #147 encerrada.
- Dropdown, loading, estados vazios, estimativas e sinais negativos cobertos por regressão.

### Corrigido — CI e conformidade documental (17/07/2026)

- Corrigido erro `E203` que bloqueava o lint do backend.
- Documentos públicos passaram a descrever fontes por função, preservando a política de não exposição de provedores.
- Auditoria arquitetural da página Resumo formalizada na issue #161.


### Corrigido — Tesouro Direto e pipeline de preços (17/07/2026)

- Corrigida a resolução canônica de RendA+ e Educa+ pelo ano comercial.
- Catálogo do Tesouro sincronizado de forma incremental e idempotente.
- Fallback do dados abertos oficiais do Tesouro passou a percorrer todos os recursos CSV oficiais.
- Parser oficial passou a tolerar BOM, espaços e variações de cabeçalho.
- Fluxo utilizado pela página Resumo passou a usar provedor primário de mercado, dados abertos oficiais do Tesouro e último preço persistido.
- Cotação passou a ser devolvida pelo ticker original da posição.
- Consultas e atualizações do ativo do Tesouro passaram a ser case-insensitive.
- Criação automática de ativos duplicados com `name=ticker` foi bloqueada.
- Testes de regressão adicionados para RendA+ 2060/2065, fallback oficial e associação de ticker.
- Valores atuais do Tesouro foram validados na interface.

### Documentado — Rebuild pré-produção (17/07/2026)

- Criada a issue #158 para a reconstrução limpa da base antes do go-live.
- Definida a ordem: backup, dry-run, limpeza controlada, COTAHIST, dados abertos oficiais do Tesouro, benchmarks, proventos, CSV da carteira, snapshots e reconciliação.
- O rebuild deixou de bloquear o desenvolvimento atual e passou a ser requisito formal de entrada em produção.

### Dependências — Auditoria Dependabot (17/07/2026)

Atualizações auditadas e integradas na `stable-15jun`:

- react-hook-form 7.81.0;
- Recharts 3.9.2;
- aiosqlite 0.22.1;
- Uvicorn 0.51.0;
- redis-py 8.0.1.

Os PRs originais #140, #139, #135, #132 e #136 foram encerrados após confirmação das integrações equivalentes #153 a #157.

Pendências formalizadas na issue #159:

- #146 — build-tools, incluindo TypeScript 7.0.2;
- #138 — ESLint e typescript-eslint;
- #137 — httpx 0.28.1;
- #133 — mypy 2.2.0.

### Planejamento — Próximo ciclo

- Página Resumo concluída; a Fase 2 de Proventos passa a ser a prioridade ativa (#165).
- O primeiro bloco de código será composto por testes de caracterização, sem mudança funcional.
- Patrimônio e Rentabilidade seguem pelas issues #148, #149, #150 e #151 após Proventos.

### Auditoria funcional canônica — 16/07/2026

- Contratos `summary.v2` e `rentabilidade.v2` estritos e versionados.
- Patrimônio intradiário separado de TWR fechado.
- Resultado separado em realizado, não realizado e proventos.
- Histórico mensal baseado no último snapshot de cada mês.
- Período completo sem corte artificial.
- `PortfolioClassSnapshot` e TWR por classe para ativos de mercado.
- CDI e IPCA servidos pelo backend a partir de séries persistidas.
- Tesouro e Renda Fixa sem falso TWR.
- Reconciliação monetária com tolerância de R$ 0,01.
- Atualização intradiária de preços a cada 90 minutos em dias úteis.

### Fontes oficiais e valuation canônico — 16/07/2026

- B3 COTAHIST adotado como histórico primário de ações, FIIs, ETFs nacionais e BDRs.
- dados abertos oficiais do Tesouro adotado como fonte oficial do catálogo e histórico do Tesouro.
- Renda Fixa valorizada por motor dedicado.
- Snapshots reconstruídos com dados persistidos.
- Cobertura parcial e retorno estimado explicitados.
- Comandos operacionais de rebuild e diagnóstico adicionados.

### Integração v2, aliases e eventos corporativos — 13/07/2026

- Cliente isolado para API v2.
- Resolução em lote de tickers antigos.
- Modelo de aliases históricos.
- Evento `TICKER_CHANGE` idempotente.
- Reconstrução automática de snapshots após importação CSV.
- Filtros interativos no modal CSV.

## Próximos focos

1. TWR dedicado de Tesouro e Renda Fixa (#149).
2. IBOV persistido (#150).
3. Remoção do serviço legado (#151).
4. Dependências pendentes (#159).
5. Rebuild pré-produção (#158).