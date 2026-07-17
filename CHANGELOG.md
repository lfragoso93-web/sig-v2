# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — Tesouro Direto e pipeline de preços (17/07/2026)

- Corrigida a resolução canônica de RendA+ e Educa+ pelo ano comercial.
- Catálogo do Tesouro sincronizado de forma incremental e idempotente.
- Fallback do Tesouro Transparente passou a percorrer todos os recursos CSV oficiais.
- Parser oficial passou a tolerar BOM, espaços e variações de cabeçalho.
- Fluxo utilizado pela página Resumo passou a usar BRAPI, Tesouro Transparente e último preço persistido.
- Cotação passou a ser devolvida pelo ticker original da posição.
- Consultas e atualizações do ativo do Tesouro passaram a ser case-insensitive.
- Criação automática de ativos duplicados com `name=ticker` foi bloqueada.
- Testes de regressão adicionados para RendA+ 2060/2065, fallback oficial e associação de ticker.
- Valores atuais do Tesouro foram validados na interface.

### Documentado — Rebuild pré-produção (17/07/2026)

- Criada a issue #158 para a reconstrução limpa da base antes do go-live.
- Definida a ordem: backup, dry-run, limpeza controlada, COTAHIST, Tesouro Transparente, benchmarks, proventos, CSV da carteira, snapshots e reconciliação.
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

- Página Resumo retorna ao topo da fila: KPIs, sinal de retorno, variação versus rentabilidade, dropdowns e consistência visual.
- Proventos permanece como segunda prioridade: cobertura por classe, seed, materialização e diagnósticos.
- Patrimônio e Rentabilidade seguem pelas issues #148, #149, #150 e #151.

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
- Tesouro Transparente adotado como fonte oficial do catálogo e histórico do Tesouro.
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

1. Página Resumo.
2. Proventos.
3. Gráficos históricos por classe (#148).
4. TWR dedicado de Tesouro e Renda Fixa (#149).
5. IBOV persistido (#150).
6. Remoção do serviço legado (#151).
7. Dependências pendentes (#159).
8. Rebuild pré-produção (#158).
