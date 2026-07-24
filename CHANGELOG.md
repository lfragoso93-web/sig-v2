# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — gate de auditoria Node.js (24/07/2026)

- O gate Node.js passou a usar `audit-ci`, preservando falha para qualquer
  vulnerabilidade nova de severidade alta ou crítica.
- A vulnerabilidade `GHSA-qwww-vcr4-c8h2` foi permitida somente no caminho
  `react-router-dom > react-router`, pois afeta RSC Mode/Server Actions e o
  frontend do SGI v2 é uma SPA Vite sem esses recursos.
- A exceção é temporária e deve ser removida assim que houver uma versão
  corrigida do React Router publicada no npm.

### Corrigido — checksum canônico do plano operacional (24/07/2026)

- A saída de `pre_prod_cleanup_plan` passou a expor `plan_sha256`.
- O checksum usa a mesma serialização JSON canônica revalidada por
  `pre_prod_isolated_cleanup`.
- O valor permanece fora do próprio `plan.json`, evitando autorreferência.
- Runbooks, README e ROADMAP foram sincronizados e proíbem substituir o valor
  por `Get-FileHash`.
- A cadeia `20260724-135540` permanece como evidência técnica, mas não autoriza
  execução após a mudança do SHA.
- Nenhuma limpeza ou operação de banco foi executada.

### Adicionado — wrapper operacional da limpeza real (24/07/2026)

- Criado `scripts/Invoke-PreProdRealCleanup.ps1` como entrada oficial em PowerShell.
- O wrapper fixa branch `stable-15jun`, perfil `sgi-pre-prod-real` e a CLI canônica.
- Origem e destino recebem a mesma URL síncrona de `PRE_PROD_SYNC_DATABASE_URL`.
- Parâmetros são encaminhados por array, sem `python -c`, `sh -lc` ou avaliação dinâmica.
- A confirmação composta continua explícita, revisada pelo operador e não é recalculada.
- O exit code da CLI é propagado sem alteração.
- Adicionados testes estruturais dos invariantes operacionais.
- Nenhuma limpeza, seed, coleta, importação, rebuild ou alteração de banco foi executada.

### Documentado — runbook da limpeza real sincronizado (24/07/2026)

- `docs/pre-prod-cleanup-execution-runbook.md` passou a documentar os perfis `sgi-pre-prod-isolated` e `sgi-pre-prod-real`.
- A cadeia `20260724-100752` foi mantida somente como evidência histórica e declarada inelegível para execução após a mudança de SHA.
- Gates, confirmação composta, códigos de saída, artefatos e reconciliação imediata foram alinhados à CLI e ao contrato atuais.
- README e ROADMAP foram sincronizados com a promoção do perfil real pela PR #204.
- O wrapper operacional oficial foi registrado como próximo bloco antes da geração de uma nova cadeia.
- Nenhuma CLI, código, banco, limpeza, seed, coleta, importação ou rebuild foi alterado ou executado.

### Adicionado — perfil seguro para limpeza real da pré-produção (24/07/2026)

- A CLI `pre_prod_isolated_cleanup` passou a aceitar dois perfis mutuamente exclusivos.
- `sgi-pre-prod-isolated` exige origem e destino diferentes.
- `sgi-pre-prod-real` exige origem e destino com a mesma identidade normalizada de host, porta e banco.
- Qualquer marcador desconhecido aborta antes da criação do engine e antes de qualquer escrita.
- O executor transacional, a confirmação composta, os checksums, o lock, as contagens e o rollback integral foram preservados.
- Foram adicionados testes específicos para impedir regressões entre os perfis.
- A validação local concluiu com 34 testes aprovados e `compileall` sem erros.
- Criado `docs/pre-prod-real-cleanup-target-profile.md`.
- README, ROADMAP e o runbook principal foram sincronizados.
- O runbook deixou de listar `app_configs` e `dividends_sync_jobs`, ausentes do inventário canônico atual de 24 tabelas.
- A cadeia `20260724-100752` foi declarada não reutilizável após a mudança do SHA.
- A limpeza real, seeds, coleta, importação e rebuild não foram executados neste bloco.

### Documentado — saneamento pós-merge da limpeza isolada (24/07/2026)

- README e ROADMAP foram sincronizados após o merge da PR #198.
- A revisão arquitetural de 23/07 foi preservada como fotografia histórica e recebeu adendo pós-merge.
- A Issue #196 foi reconciliada com todos os blocos concluídos e permanece encerrada.
- A Issue-mãe #158 foi atualizada com o progresso real e a ordem remanescente do rebuild.
- Criada a Issue #199 como único gate operacional para autorizar a limpeza na pré-produção real.
- A limpeza real, seeds, coleta, importação e rebuild não foram executados neste bloco.
- O histórico completo deste changelog foi restaurado após nova detecção de truncamento documental.

### Concluído — ensaio integral da limpeza isolada (23/07/2026)

- A CLI captura automaticamente baseline e pós-contagem de todas as tabelas do contrato canônico.
- São publicados `preserved-before.json`, `preserved-after.json`, `post-cleanup-inventory.json` e `reconciliation.json` sem sobrescrita.
- Adicionado `--rehearsal-fail-after-table`, restrito ao `cleanup_order`, para comprovar rollback integral.
- O cenário de sucesso `20260723-213000` removeu 4.673.054 linhas planejadas, preservou tabelas fora do plano e retornou `ok=true`.
- O cenário de rollback `20260723-213001` retornou exit code `22`, `committed=false`, contagens iguais ao baseline e `ok=true`.
- Os bancos descartáveis foram removidos. A limpeza da pré-produção real não foi executada.
- A PR #198 foi promovida para a `main` e a Issue #196 foi encerrada.

### Corrigido — revisão arquitetural integral (23/07/2026)

- Adicionado `docs/ARCHITECTURAL_REVIEW_2026-07-23.md` com arquitetura, riscos, dívida técnica e fila priorizada.
- Corrigida a publicação de `cleanup/execution.json` no Windows.
- Corrigidos testes frontend obsoletos de portfólios, evolução e normalização do contrato `summary.v2`.
- Atualizado `backend/TESTING.md` para refletir a suíte real.
- Atualizada a documentação da introspecção para refletir a integração concluída.

### Documentado — preparação do ensaio isolado da limpeza (23/07/2026)

- Criado o runbook `docs/pre-prod-isolated-cleanup-rehearsal-runbook.md` para o Bloco D0 da Issue #196.
- O procedimento define gates de branch, SHA, backup v3, banco descartável, plano aprovado, ausência de processos concorrentes e confirmação composta.
- Foram documentados comandos PowerShell para restauração, execução, reconciliação, rollback e descarte.
- A limpeza na base pré-produção real permaneceu proibida.

### Adicionado — evidência de aborto e rollback da limpeza isolada (23/07/2026)

- `cleanup/execution.json` registra divergência prévia, lock indisponível e rollback após autorização completa.
- Estados de falha são limitados a `aborted` e `rolled_back`, com motivos estáveis.
- Mensagens brutas de exceção, URLs e credenciais não são persistidas.
- Logs pós-autorização foram redigidos.
- A publicação permanece UTF-8, atômica, durável e sem sobrescrita.
- Testes cobrem divergência, rollback, zero escritas persistidas e ausência de segredos.

### Adicionado — CLI da limpeza isolada (23/07/2026)

- Adicionada a CLI `python -m app.cli.pre_prod_isolated_cleanup`, inicialmente exclusiva para PostgreSQL isolado.
- A entrada lê `cleanup/plan.json` em UTF-8, revalida branch, SHA, identidade e checksum e exige confirmação composta.
- Origem e destino são comparados por host, porta e banco.
- Exit codes distinguem entrada, identidade, alvo, confirmação, divergência, lock, rollback e artefato.
- URLs e credenciais não são impressas nem persistidas.

### Adicionado — autorização pura da limpeza isolada (23/07/2026)

- Adicionado o contrato `pre-prod-isolated-cleanup.v1`.
- A autorização exige confirmação vinculada a `run_id`, banco, commit e checksum canônico.
- O plano `pre-prod-cleanup-execution.v1` é revalidado quanto a schema, modo, branch, blockers, identidade, checksum e ordem.
- Testes unitários cobrem adulteração, confirmação inexata, alvo igual à origem e marcador ausente.

### Corrigido — migração Pydantic v2 para ConfigDict (22/07/2026)

- Configurações baseadas em `class Config` foram migradas para `ConfigDict` ou `SettingsConfigDict`.
- Ocorrências adicionais em ativos, proventos, Tesouro e `AssetListItem` foram incorporadas.
- A regressão estrutural percorre todo o backend via AST.
- A validação final passou com `666 passed`, `1 skipped` e zero `PydanticDeprecatedSince20`.
- A Issue #186 foi encerrada; timestamps UTC naive seguem na Issue #192.

### Concluído — exportação auditável pré-produção (22/07/2026)

- Adicionado o contrato `pre-prod-export.v1` para tabelas `export_before_cleanup`.
- Exportação CSV determinística com manifesto, contagens, bytes, SHA-256 de dados e schema.
- O gate e a exportação compartilham snapshot `REPEATABLE READ READ ONLY`.
- Adicionada a CLI `python -m app.cli.pre_prod_export`.
- Artefatos são publicados atomicamente sem sobrescrita.
- Corrigida a normalização de `ordinal_position` segundo a projeção CSV.
- A execução `20260722-134741` exportou 3 tabelas, 323 linhas e 47.576 bytes com `reconciled=true`.

### Concluído — dry-run de limpeza pré-produção (22/07/2026)

- Adicionado o contrato `pre-prod-cleanup-impact.v2`.
- DAG reutilizável e introspecção read-only de foreign keys produzem ordens seguras.
- A CLI `pre_prod_cleanup_impact` publica relatório auditável sem executar limpeza.
- O dry-run `20260722-101848` registrou 24 tabelas, 4.673.320 linhas, zero blockers e zero ciclos.
- O gate de exportação foi confirmado para `transactions`, `fixed_income_investments` e `corporate_events`.

### Corrigido — consistência temporal do backup PostgreSQL (21/07/2026)

- O backup v2 revelou divergência temporal por snapshots distintos entre inventário e dump.
- O contrato evoluiu para `pre-prod-backup.v3` com snapshot PostgreSQL compartilhado.
- O `pg_dump` recebe `--snapshot` e o manifesto registra `consistent_snapshot=true`.
- O restore recusa backups v1/v2 e manifestos temporalmente inconsistentes.
- A origem permaneceu com zero escritas.

### Corrigido — compatibilidade do backup PostgreSQL (20/07/2026)

- A imagem backend passou a usar clientes PostgreSQL 16, alinhados ao servidor.
- O contrato v2 registra majors do cliente e servidor e aborta quando divergem.
- O restore recusa archives legados incompatíveis.

### Corrigido — auditoria de dependências da PR #184 (20/07/2026)

- `brace-expansion` transitivo foi atualizado de 5.0.6 para 5.0.7.
- O `package-lock.json` foi reconciliado com `typescript@6.0.3`.
- `npm audit --audit-level=high` passou com zero vulnerabilidades.

### Adicionado — backup e restauração isolada pré-produção (20/07/2026)

- Adicionado o CLI `pre_prod_backup` com branch, SHA, inventário v2, dump custom, inspeção e checksum.
- Adicionado o CLI `pre_prod_restore` com confirmação, recusa da origem, destino vazio e restore atômico.
- O inventário é reexecutado após a restauração.
- A reconciliação compara migrations, tabelas, políticas, contagens e achados.
- URLs são redigidas dos manifestos e relatórios.
- Artefatos são persistidos em `artifacts/pre-prod-rebuild/<run-id>/`.

### Concluído — classificação integral do inventário pré-produção (20/07/2026)

- O contrato de inventário evoluiu para `pre-prod-inventory.v2`.
- As 24 tabelas observadas receberam classificação e justificativa explícitas.
- Metas, configurações, auditoria e dados fiscais são preservados.
- Transações, renda fixa e eventos corporativos exigem exportação.
- Catálogo, preços, PTAX, séries, proventos, posições e snapshots são reconstruíveis.
- Tabelas futuras continuam `unclassified`.

### Adicionado — inventário pré-produção read-only (20/07/2026)

- Criado o contrato `pre-prod-inventory.v1`.
- O relatório inclui contagens, aliases duplicados, órfãos, preços duplicados e snapshots duplicados.
- A CLI executa somente consultas e encerra a sessão com rollback.
- Testes impedem comandos de escrita durante o inventário.
- A execução inicial registrou 24 tabelas, 4.671.361 linhas e zero inconsistências canônicas.

### Corrigido — compatibilidade do build frontend (20/07/2026)

- TypeScript 7.0.2 foi revertido para 6.0.3 por incompatibilidade com `typescript-eslint@8.64.0`.
- A correção preservou resolução estrita de peer dependencies.
- O build Docker foi confirmado e a Issue #182 foi encerrada.

### Corrigido — validação pré-merge da Fase 3 (20/07/2026)

- Componentes frontend órfãos que importavam `usePerformance.ts` foram removidos.
- O typecheck global deixou de depender do cliente eliminado.
- Consumidores canônicos atuais foram preservados.

### Concluído — Fase 3 Patrimônio (20/07/2026)

- Evolução consolidada e por classe passou a consumir snapshots canônicos.
- Períodos usam fronteiras determinísticas de meses-calendário.
- Estados de loading, erro, vazio, backfill e classe sem motor são distintos.
- Tooltips apresentam patrimônio, custo, resultados, TWR, fonte e cobertura.
- Reconciliações usam a mesma data de referência.
- Clientes órfãos e endpoints legados foram removidos.
- TWR de Tesouro e Renda Fixa permanece na Issue #149.

### Concluído — Fase 2 Proventos (19/07/2026)

- Pipeline DB-first consolidado entre evento global, direito materializado e pagamento.
- Coleta diária baseada no catálogo global de ativos elegíveis.
- Leitura separada de materialização.
- Contratos estritos e filtros compartilhados.
- Eventos monetários e não monetários normalizados.
- Histórico mensal reconciliado por classe.
- Frontend diferencia loading, erro e vazio.
- Migração destrutiva de campos legados permanece reservada à Issue #158.

### Planejamento — Fase 2 Proventos (18/07/2026)

- Página Resumo promovida pela PR #164.
- Criada a Issue-mãe #165.
- Arquitetura auditada e sequência de implementação definida.

### Corrigido — Página Resumo (18/07/2026)

- KPIs reconciliados entre Resumo, Patrimônio e valuation canônico.
- `summary.v2` e posições validados nas fronteiras backend e frontend.
- Resultado atual cobre vendas parciais, posições encerradas e carteiras mistas.
- Cobertura parcial, snapshots, sinais negativos e dropdown foram corrigidos.

### Corrigido — CI e conformidade documental (17/07/2026)

- Corrigido erro `E203` no lint backend.
- Documentos públicos passaram a descrever fontes por função.
- Auditoria arquitetural da página Resumo formalizada na Issue #161.

### Corrigido — Tesouro Direto e pipeline de preços (17/07/2026)

- RendA+ e Educa+ passaram a ser resolvidos pelo ano comercial.
- Catálogo do Tesouro sincronizado de forma incremental e idempotente.
- Fallback oficial percorre recursos CSV oficiais.
- Parser tolera BOM, espaços e variações de cabeçalho.
- Fluxo do Resumo usa fonte recente, fallback oficial e último preço persistido.
- Tickers e aliases são tratados case-insensitivamente.
- Criação automática de ativos duplicados foi bloqueada.

### Documentado — Rebuild pré-produção (17/07/2026)

- Criada a Issue #158 para reconstrução limpa antes do go-live.
- Definida a ordem backup, dry-run, limpeza, seeds, CSV, snapshots e reconciliação.

### Dependências — Auditoria Dependabot (17/07/2026)

- Atualizações compatíveis foram auditadas e integradas em commits isolados.
- A Issue #159 foi encerrada após não restarem PRs Dependabot abertas.
- A regressão de TypeScript 7 foi separada na Issue #182.

### Auditoria funcional canônica — 16/07/2026

- Contratos `summary.v2` e `rentabilidade.v2` estritos e versionados.
- Patrimônio intradiário separado de TWR fechado.
- Resultado realizado, não realizado e proventos separados.
- Histórico mensal pelo último snapshot de cada mês.
- CDI e IPCA servidos de séries persistidas.
- Tesouro e Renda Fixa sem falso TWR.
- Reconciliação monetária com tolerância de R$ 0,01.

### Fontes oficiais e valuation canônico — 16/07/2026

- B3 COTAHIST adotado como histórico primário de renda variável brasileira.
- Dados oficiais do Tesouro adotados para catálogo e histórico.
- Renda Fixa valorizada por motor dedicado.
- Snapshots reconstruídos com dados persistidos.
- Cobertura parcial e retorno estimado explicitados.

### Integração v2, aliases e eventos corporativos — 13/07/2026

- Cliente isolado para API v2.
- Resolução em lote de tickers antigos.
- Modelo de aliases históricos.
- Evento `TICKER_CHANGE` idempotente.
- Reconstrução automática de snapshots após importação CSV.
- Filtros interativos no modal CSV.

## Próximos focos

1. Promover a exposição oficial do checksum canônico do plano.
2. Gerar nova cadeia operacional vinculada ao novo SHA promovido.
3. Executar e reconciliar a limpeza real pela Issue #199.
4. Endurecer ou remover o router administrativo de debug.
5. Remover o serviço legado de rentabilidade (#151).
6. Materializar IBOV (#150).
7. Implementar TWR dedicado por classe (#149).
8. Migrar timestamps UTC legados para timezone-aware (#192).
