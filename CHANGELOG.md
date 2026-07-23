# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Adicionado — evidência de aborto e rollback da limpeza isolada (23/07/2026)

- `cleanup/execution.json` agora também registra divergência prévia, lock indisponível e rollback após autorização completa.
- Estados de falha são limitados a `aborted` e `rolled_back`, com motivos estáveis controlados pela aplicação.
- Mensagens brutas de exceção, URLs e credenciais não são persistidas no artefato.
- Logs pós-autorização foram redigidos para impedir vazamento de detalhes sensíveis no console.
- A publicação continua UTF-8, atômica, durável e sem sobrescrita.
- Testes com mocks cobrem divergência de contagem, rollback por pós-condição, zero escritas persistidas e ausência de segredos.
- Nenhuma execução da CLI contra PostgreSQL foi realizada neste bloco.

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
