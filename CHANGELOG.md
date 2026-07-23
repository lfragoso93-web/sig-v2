# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Concluído — ensaio integral da limpeza isolada (23/07/2026)

- A CLI agora captura automaticamente baseline e pós-contagem de todas as
  tabelas do contrato canônico e publica `preserved-before.json`,
  `preserved-after.json`, `post-cleanup-inventory.json` e
  `reconciliation.json` sem sobrescrita.
- Adicionado mecanismo explícito `--rehearsal-fail-after-table`, restrito ao
  `cleanup_order`, para comprovar rollback integral dentro da transação.
- O cenário de sucesso `20260723-213000`, executado somente em restauração
  descartável do backup v3, removeu 4.673.054 linhas planejadas,
  preservou as tabelas fora do plano e retornou reconciliação `ok=true`.
- O cenário de rollback `20260723-213001`, em segunda restauração limpa,
  retornou exit code `22`, `committed=false`, contagens finais idênticas ao
  baseline e reconciliação `ok=true`.
- Os três bancos descartáveis do ensaio foram removidos após a validação. A
  limpeza da pré-produção real continua proibida e não foi executada.

### Corrigido — revisão arquitetural integral (23/07/2026)

- Adicionado `docs/ARCHITECTURAL_REVIEW_2026-07-23.md` com estado, arquitetura, riscos, dívida técnica, revisão das 15 Issues abertas, revisão da PR #198 e fila P0–P3.
- Corrigida a publicação de `cleanup/execution.json` no Windows, preservando `fsync` de diretório nas plataformas que o suportam.
- Corrigidos testes frontend obsoletos de portfólios, evolução e normalização do contrato `summary.v2`.
- Atualizado `backend/TESTING.md`; a suíte possui mais de 100 módulos rastreados, não 21.
- Atualizada a documentação da introspecção para refletir a integração concluída com `pre-prod-cleanup-impact.v2`.
- O Actions da PR #198 permanece bloqueado por billing/limite da conta; nenhum job chegou a executar código.
- Nenhuma limpeza, seed, coleta, restore ou rebuild foi executado nesta revisão.

### Documentado — preparação do ensaio isolado da limpeza (23/07/2026)

- Criado o runbook `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md` para o Bloco D0 da Issue #196.
- O procedimento define gates de branch, SHA, backup v3, banco descartável, plano aprovado, ausência de processos concorrentes e confirmação composta.
- Foram documentados comandos PowerShell para restauração, execução, reconciliação, cenário obrigatório de rollback e descarte do banco.
- A limpeza na base pré-produção real permanece proibida; nenhuma restauração, limpeza, seed, coleta ou rebuild foi executado neste bloco.

### Adicionado — evidência de aborto e rollback da limpeza isolada (23/07/2026)

- `cleanup/execution.json` agora também registra divergência prévia, lock indisponível e rollback após autorização completa.
- Estados de falha são limitados a `aborted` e `rolled_back`, com motivos estáveis controlados pela aplicação.
- Mensagens brutas de exceção, URLs e credenciais não são persistidas no artefato.
- Logs pós-autorização foram redigidos para impedir vazamento de detalhes sensíveis no console.
- A publicação continua UTF-8, atômica, durável e sem sobrescrita.
- Testes com mocks cobrem divergência de contagem, rollback por pós-condição, zero escritas persistidas e ausência de segredos.
- A validação multiplataforma dos Blocos B e C foi concluída com 44 testes aprovados e `compileall` sem erros.

### Adicionado — CLI da limpeza isolada (23/07/2026)

- Adicionada a CLI `python -m app.cli.pre_prod_isolated_cleanup`, exclusiva para PostgreSQL isolado.
- A entrada operacional lê `cleanup/plan.json` em UTF-8, revalida branch, SHA, identidade e checksum e exige confirmação composta por argumento explícito.
- Origem e destino são comparados por host, porta e banco; o destino exige o marcador `sgi-pre-prod-isolated` e driver PostgreSQL síncrono.
- Códigos de saída distintos separam entrada inválida, identidade, alvo, confirmação, divergência de contagem, lock, rollback e artefato.
- URLs e credenciais não são impressas nem persistidas; somente `host:port/database` pode aparecer no relatório.
- Testes unitários com mocks comprovam aborto antes da criação do engine quando os gates falham e descarte do engine em divergências.
- Nenhuma execução da CLI contra PostgreSQL foi realizada neste bloco.

### Adicionado — autorização pura da limpeza isolada (23/07/2026)

- Adicionado o contrato versionado `pre-prod-isolated-cleanup.v1`, separado do contrato `plan-only` existente.
- A autorização exige confirmação composta vinculada a `run_id`, banco de destino, commit SHA completo e checksum SHA-256 canônico do plano.
- Origem e destino são comparados por host, porta e banco; o destino deve ser diferente e portar o marcador explícito `sgi-pre-prod-isolated`.
- O plano `pre-prod-cleanup-execution.v1` é revalidado quanto a schema, modo, branch, blockers, identidade, checksum, ordem e histórico de segurança.
- A serialização do contrato remove o texto de confirmação e não inclui URLs ou credenciais.
- Testes unitários sem banco cobrem adulteração do plano, confirmação inexata, alvo igual à origem e ausência do marcador de isolamento.
- Nenhum executor, conexão com banco ou SQL destrutivo foi introduzido neste bloco.

### Corrigido — migração Pydantic v2 para ConfigDict (22/07/2026)

- Configurações baseadas em `class Config` foram migradas para `ConfigDict` ou `SettingsConfigDict`.
- A validação local revelou quatro ocorrências adicionais não identificadas no primeiro mapeamento: `AssetRead`, `DividendRead`, `TreasuryPositionResponse` e `AssetListItem`.
- A regressão estrutural agora percorre todo o backend via AST e falha caso qualquer nova `class Config` seja introduzida.
- Testes preservam `from_attributes`, carregamento de `.env` e `case_sensitive=True`.
- A validação final passou com `666 passed`, `1 skipped` intencional e zero `PydanticDeprecatedSince20`.
- A Issue #186 foi encerrada; os warnings remanescentes de `datetime.utcnow()` foram separados na Issue #192.

### Concluído — exportação auditável pré-produção (22/07/2026)

- Adicionado o contrato versionado `pre-prod-export.v1` para exportações auditáveis das tabelas classificadas como `export_before_cleanup`.
- Adicionado o serviço de exportação CSV determinística com manifesto, contagens, tamanho em bytes, SHA-256 de dados e SHA-256 de schema.
- O gate `pre-prod-cleanup-impact.v2` e a exportação compartilham uma única sessão e um único snapshot PostgreSQL `REPEATABLE READ READ ONLY`.
- Adicionada a CLI `python -m app.cli.pre_prod_export`, com exit codes distintos para sucesso, falha operacional, gate bloqueado, divergência de reconciliação e interrupção.
- Artefatos são publicados atomicamente em `artifacts/pre-prod-rebuild/<run-id>/export`, sem sobrescrever execuções anteriores.
- O runbook `docs/pre-prod-export-runbook.md` documenta execução PowerShell, artefatos, critérios de validação e códigos de saída.
- Corrigida a introspecção de schema para normalizar `ordinal_position` segundo a projeção CSV, preservando ordinais contíguos mesmo quando o PostgreSQL mantém lacunas após remoção de colunas.
- A execução real `20260722-134741` exportou `corporate_events`, `fixed_income_investments` e `transactions`: 3 tabelas, 323 linhas e 47.576 bytes.
- A validação real retornou `reconciled=true`, exit code `0`, `source_writes_executed=0`, `cleanup_executed=false`, `rebuild_executed=false` e `overwrite_performed=false`.

### Concluído — dry-run de limpeza pré-produção (22/07/2026)

- Adicionado o contrato versionado `pre-prod-cleanup-impact.v2`, derivado do inventário canônico `pre-prod-inventory.v2`.
- Adicionados DAG reutilizável e introspecção read-only de foreign keys para produzir ordens seguras de limpeza e reconstrução.
- O plano identifica dependências, gate de exportação, ciclos referenciais e bloqueadores sem executar limpeza, exportação ou rebuild.
- Adicionada a CLI `python -m app.cli.pre_prod_cleanup_impact`, com validação de branch/SHA, artefato JSON auditável e exit codes distintos para aprovação, bloqueio e falha operacional.
- Relatórios aprovados e bloqueados são preservados em `artifacts/pre-prod-rebuild/<run-id>/cleanup-impact.json`, sem sobrescrita de execuções anteriores.
- O runbook `docs/pre-prod-cleanup-impact-runbook.md` documenta execução, critérios de aborto, paths e leitura dos códigos de saída.
- A suíte relacionada passou com 45 testes e zero falhas; cinco warnings de configuração Pydantic v2 foram registrados separadamente na Issue #186.
- O dry-run real `20260722-101848` foi executado no PostgreSQL: 24 tabelas, 4.673.320 linhas, 11 preservadas, 3 com exportação obrigatória e 10 reconstruíveis.
- A execução real retornou `ok=true`, exit code `0`, zero bloqueios, zero ciclos, `writes_executed=0`, `cleanup_executed=false` e `rebuild_executed=false`.
- O gate de exportação foi confirmado para `transactions`, `fixed_income_investments` e `corporate_events`.

### Corrigido — consistência temporal do backup PostgreSQL (21/07/2026)

- O backup v2 foi restaurado integralmente em banco isolado, com checksum válido, migrations e 24 tabelas reconciliadas.
- A reconciliação detectou 998 linhas adicionais de `asset_prices` no dump porque o inventário e o `pg_dump` usavam snapshots distintos enquanto a coleta seguia ativa.
- O contrato evoluiu para `pre-prod-backup.v3`: inventário e dump agora compartilham um snapshot PostgreSQL exportado em transação `REPEATABLE READ READ ONLY`.
- O `pg_dump` recebe `--snapshot`, e o manifesto registra `consistent_snapshot=true`.
- O restore recusa backups v1/v2 e manifestos sem comprovação de snapshot consistente.
- Testes cobrem propriedade da transação, snapshot obrigatório, propagação ao dump e rejeição de artefatos temporalmente inconsistentes.
- A origem permaneceu com zero escritas; nenhuma limpeza ou rebuild foi executado.

### Corrigido — compatibilidade do backup PostgreSQL (20/07/2026)

- Corrigida a imagem backend para executar `pg_dump`, `pg_restore` e `psql` do PostgreSQL 16, alinhados ao servidor.
- O contrato evoluiu para `pre-prod-backup.v2` e registra os majors do cliente e do servidor.
- O backup aborta antes do dump quando os majors divergem.
- O restore recusa archives v1 que podem conter parâmetros incompatíveis, como `transaction_timeout`.
- Testes cobrem incompatibilidade de major e rejeição do contrato legado.
- A tentativa real v1 abortou de forma segura dentro da transação isolada, com zero escritas na origem e sem limpeza ou rebuild.

### Corrigido — auditoria de dependências da PR #184 (20/07/2026)

- `brace-expansion` transitivo foi atualizado de 5.0.6 para 5.0.7, corrigindo `GHSA-3jxr-9vmj-r5cp`.
- O `package-lock.json` foi reconciliado com `typescript@6.0.3` e deixou de carregar os binários opcionais órfãos do TypeScript 7.
- `npm audit --audit-level=high` passou com zero vulnerabilidades.

### Adicionado — backup e restauração isolada pré-produção (20/07/2026)

- Adicionado o CLI `pre_prod_backup` com trava da branch, SHA Git completo, inventário v2 da origem, `pg_dump` custom, arquivo não vazio, inspeção por `pg_restore --list` e checksum SHA-256.
- Adicionado o CLI `pre_prod_restore` com confirmação explícita, recusa da origem, nome de banco diferente, preflight de destino vazio e restore atômico com falha imediata.
- O inventário `pre-prod-inventory.v2` é executado novamente na restauração.
- A reconciliação compara migrations, tabelas, políticas, contagens e achados e só aprova com zero bloqueios.
- URLs de banco são redigidas dos manifestos e relatórios; a origem registra zero escritas.
- Artefatos são persistidos em `artifacts/pre-prod-rebuild/<run-id>/` e excluídos do Git.
- A imagem backend passou a incluir os clientes PostgreSQL exigidos.
- Testes cobrem dump vazio, destino original, destino não vazio, credenciais e divergências.
- O procedimento e os critérios de abortar foram sincronizados no runbook e em `docs/operations.md`.
- A implementação da Issue #183 está pronta; sua conclusão depende da execução no PostgreSQL real e de `reconciliation-report.json` com `ok=true`.

### Concluído — classificação integral do inventário pré-produção (20/07/2026)

- O contrato de inventário foi evoluído para `pre-prod-inventory.v2`.
- As 24 tabelas observadas no PostgreSQL real passaram a ter classificação e justificativa arquitetural explícitas.
- Metas, configurações, auditoria e dados fiscais são preservados.
- Transações, renda fixa e eventos corporativos exigem exportação antes de qualquer limpeza.
- Catálogo, preços, PTAX, séries, proventos, posições e snapshots permanecem reconstruíveis.
- Tabelas futuras continuam `unclassified` e fazem o CLI retornar código diferente de zero.
- A saída do CLI foi padronizada em UTF-8 para evitar corrupção de acentos no PowerShell.
- O runbook e o ROADMAP foram sincronizados; o próximo bloqueio é backup com checksum e restauração isolada.

### Adicionado — inventário pré-produção read-only (20/07/2026)

- Criado o contrato versionado `pre-prod-inventory.v1` para inventário da base antes do rebuild.
- Tabelas são classificadas como preservadas, exportáveis antes da limpeza, reconstruíveis ou não classificadas.
- O relatório inclui contagens por tabela, aliases duplicados, aliases e preços órfãos, preços duplicados e snapshots consolidados duplicados.
- O CLI `python -m app.cli.pre_prod_inventory` executa somente consultas e sempre encerra a sessão com rollback.
- Testes com SQLite instrumentado impedem `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `DROP`, `ALTER` e `CREATE` durante o inventário.
- `docs/operations.md`, README e ROADMAP foram sincronizados com a Issue #176 e o runbook da Issue #158.
- A execução inicial no PostgreSQL real registrou 24 tabelas, 4.671.361 linhas e zero inconsistências canônicas.

### Corrigido — compatibilidade do build frontend (20/07/2026)

- TypeScript 7.0.2 foi revertido para 6.0.3 por incompatibilidade declarada com `typescript-eslint@8.64.0`.
- A correção preservou resolução estrita de peer dependencies, sem `--force` ou `--legacy-peer-deps`.
- O usuário confirmou o build Docker normal e a Issue #182 foi encerrada.
- A auditoria Dependabot da Issue #159 permanece concluída.

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

### Planejamento — Fase 2 Proventos (18/07/2026)

- Página Resumo concluída e promovida para a `main` pela PR #164.
- Criada a Issue-mãe #165 para reconstrução e validação ponta a ponta de Proventos.
- Arquitetura atual auditada, incluindo contratos temporais, filtros divergentes, escrita durante leitura, serviços paralelos e legado de modelo.
- Definida a sequência: testes de caracterização, contratos e filtros, separação de leitura/materialização, consolidação do pipeline, validação por classe e revisão do frontend.
- Issues #92 e #95 preservadas como entregas concluídas; #131 vinculada como sub-bloco posterior.

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
- Fallback dos dados abertos oficiais do Tesouro passou a percorrer todos os recursos CSV oficiais.
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

- Atualizações compatíveis foram auditadas e integradas na `stable-15jun` em commits isolados.
- A Issue #159 foi encerrada após não restarem PRs Dependabot abertos.
- A regressão específica de TypeScript 7 foi tratada separadamente na Issue #182.

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
- Dados abertos oficiais do Tesouro adotados como fonte oficial do catálogo e histórico do Tesouro.
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

1. Concluir o ensaio da limpeza controlada em banco PostgreSQL descartável no escopo da Issue #196.
2. Remover o serviço legado de rentabilidade (#151).
3. Materializar IBOV (#150).
4. Implementar TWR dedicado por classe (#149).
5. Migrar timestamps UTC legados para timezone-aware (#192).
