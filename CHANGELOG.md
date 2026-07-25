# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em Keep a Changelog.

## [Unreleased] — branch `stable-15jun`

### Corrigido — resolução do wrapper nos testes em container (25/07/2026)

- O teste estrutural do wrapper deixou de subir três níveis a partir de `backend/tests/unit`, o que resolvia incorretamente a raiz como `/` dentro do container.
- A raiz do repositório em runtime agora é derivada como `/app`, preservando o caminho canônico `/app/scripts/Invoke-PreProdTreasuryIdempotency.ps1`.
- Foi adicionada uma regressão explícita que exige a existência do script no caminho resolvido antes das demais verificações estruturais.
- Nenhum seed, comparador ou escrita em pré-produção foi executado neste bloco.

### Corrigido — encoding das evidências de idempotência do Tesouro (25/07/2026)

- O wrapper deixou de usar `Tee-Object -FilePath`, cujo encoding implícito no Windows PowerShell produziu evidências UTF-16 incompatíveis com o contrato JSON UTF-8.
- `first.json`, `second.json` e `idempotency.json` agora são persistidos explicitamente como UTF-8 sem BOM por `System.IO.File.WriteAllText`.
- O exit code nativo de cada comando Docker é capturado antes da renderização e persistência da saída.
- Testes estruturais cobrem o encoding explícito, a ausência de `Tee-Object -FilePath` e a preservação dos exit codes.
- O incidente ocorreu somente no comparador offline: as duas execuções do seed retornaram `ok=true`, `required_empty_payloads=0`, integridade reconciliada e estado final estável em 88.638 preços.

### Corrigido — classificação de payloads vazios do Tesouro (25/07/2026)

- O histórico oficial passou a separar payloads vazios bloqueantes de ausências esperadas para títulos vencidos.
- `history.empty_payloads` foi preservado como total auditável, com os novos campos `required_empty_payloads`, `expected_empty_payloads`, `required_empty_symbols` e `expected_empty_symbols`.
- Símbolos com vencimento `DDMMAAAA` usam a data exata; séries com ano apenas são consideradas vencidas após `31/12` do ano publicado.
- Símbolos sem vencimento reconhecível permanecem bloqueantes por segurança.
- O orquestrador agora falha somente quando `required_empty_payloads` é diferente de zero, mantendo compatibilidade com evidências antigas que publicam apenas `empty_payloads`.
- Testes cobrem títulos vigentes, vencidos, símbolos sem vencimento, ausência esperada, ausência bloqueante e contrato legado.
- O runbook foi sincronizado com o incidente operacional, o rollback confirmado e os novos critérios de aborto e sucesso.

### Adicionado — wrapper operacional de idempotência do Tesouro (25/07/2026)

- Criado `scripts/Invoke-PreProdTreasuryIdempotency.ps1` como entrada oficial para duas execuções consecutivas do seed isolado do Tesouro.
- O wrapper exige branch `stable-15jun`, `HEAD` igual ao SHA informado e confirmação exata `EXECUTE-TREASURY-IDEMPOTENCY:<SHA40>` antes de qualquer Docker.
- São gerados dois `run_id` distintos e preservados `first.json`, `second.json` e `idempotency.json` em diretório operacional determinístico.
- `ArtifactRoot` passou a aceitar somente caminhos relativos dentro de `artifacts`, com separação explícita entre caminhos do host e `/app/artifacts/...` no container.
- O comparador canônico offline é executado após as duas evidências e seu exit code é propagado sem alteração.
- Testes estruturais cobrem confirmação, identidade Git, duas execuções, volume de artefatos e ausência de avaliação dinâmica.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Os CIs #664 e #666 foram aprovados; nenhum seed, banco ou fonte oficial foi acessado durante a implementação.

### Adicionado — prova offline de idempotência do seed do Tesouro (25/07/2026)

- Criado o contrato puro `pre-prod-treasury-seed-idempotency.v1` para comparar
  duas evidências consecutivas do seed isolado do Tesouro.
- A comparação exige `run_id` distintos, mesma branch, mesmo `commit_sha`,
  baseline encadeado, contagens finais estáveis e cobertura temporal estável.
- Adicionada a CLI offline
  `python -m app.cli.pre_prod_treasury_seed_idempotency` para ler dois arquivos
  JSON UTF-8 e publicar o relatório canônico sem acessar banco ou rede.
- Os códigos de saída distinguem idempotência comprovada (`0`), divergência
  estrutural (`1`) e entrada ou contrato inválido (`2`).
- Testes cobrem sucesso, identidade divergente, estado instável, execução com
  falha, JSON inválido e arquivo ausente.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Nenhum seed, coleta ou escrita foi executado na pré-produção.

### Adicionado — identidade operacional do seed do Tesouro (25/07/2026)

- O contrato `pre-prod-treasury-seed.v1` passou a registrar `run_id`, branch e
  `commit_sha` no JSON final.
- A CLI exige `run_id` no formato `YYYYMMDD-HHMMSS`, branch `stable-15jun` e
  SHA Git hexadecimal minúsculo com 40 caracteres.
- A identidade é validada antes da abertura de qualquer sessão de banco.
- Entrada inválida retorna código operacional `1`, sem traceback e sem acesso
  ao banco.
- Testes de contrato, serviço e CLI cobrem serialização, propagação e rejeição
  segura da identidade.
- README, ROADMAP e o runbook do Tesouro foram sincronizados.
- Nenhum seed, coleta ou escrita foi executado na pré-produção.

### Adicionado — seed transacional isolado do Tesouro Direto (25/07/2026)

- Criado o contrato `pre-prod-treasury-seed.v1` com baseline, pós-contagens,
  cobertura temporal e validações de integridade.
- Catálogo e histórico oficial do Tesouro passaram a compartilhar uma única
  sessão de trabalho e são executados com `commit=False`.
- O orquestrador confirma o estágio somente após a inspeção final reconciliada
  e executa rollback integral em erro, divergência ou exceção.
- Um advisory lock PostgreSQL dedicado impede execuções concorrentes.
- Criada a CLI `python -m app.cli.pre_prod_treasury_seed` com saída JSON e
  códigos distintos para sucesso, falha operacional, concorrência e falha inesperada.
- Adicionados testes unitários de contrato, inspeção, sessão, commit, rollback e CLI.
- Criado `docs/pre-prod-treasury-seed-runbook.md` e sincronizados README e ROADMAP.
- O CI da PR #209 passou; nenhuma execução, coleta ou escrita foi realizada na pré-produção.

### Corrigido — ajuda não destrutiva das CLIs do Tesouro (25/07/2026)

- As quatro CLIs operacionais do Tesouro passaram a validar argumentos com
  `argparse` antes de abrir sessão de banco ou iniciar qualquer serviço.
- `--help` agora imprime a interface e encerra com código `0`, sem sincronizar,
  reconstruir ou auditar dados.
- Argumentos desconhecidos deixam de ser silenciosamente ignorados.
- Adicionada regressão parametrizada cobrindo catálogo, rebuild oficial e as
  duas auditorias.

### Adicionado — estágio isolado B3 COTAHIST (24/07/2026)

- Criada a CLI `pre_prod_b3_seed` para executar somente catálogo nacional e
  histórico oficial COTAHIST, sem Tesouro, cripto, benchmarks, proventos ou snapshots.
- Período e data de corte são obrigatórios e aparecem no JSON final.
- O estágio registra contagens de ativos e preços antes/depois, resultados do
  catálogo e COTAHIST e retorna exit code diferente de zero diante de erros.
