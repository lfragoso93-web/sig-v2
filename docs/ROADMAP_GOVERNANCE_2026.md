# SGI v2 — Governed Development Roadmap 2026

> **Data de Emissão**: 20 de Outubro de 2026  
> **Status**: Vigente / Aprovado para Planejamento e Execução  
> **Autoridade de Governança**: `docs/ISSUE_GOVERNANCE.md`, `ROADMAP.md` e Skills SGI (`sgi-development`, `sgi-certification`, `sgi-financial-data`, `sgi-market-data`)  
> **Baseline Operacional**: Branch `stable-15jun` (`a517e8871e42142cc77943d08f59bcc0d3a6946e`) | Branch `main` (`4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`)  
> **Ambiente Runtime de Referência**: Compose `sig-v2` (`sig-v2-backend-1`, `sig-v2-frontend-1`, `sig-v2-db-1`, `sig-v2-redis-1`, `sig-v2-cloudflared-1`)

---

## 1. Visão Executiva e Princípios de Governança

O presente **Roadmap de Governança 2026** consolida o planejamento estratégico, técnico e operacional do **SGI v2** (Sistema de Gestão Financeira e Patrimonial). Ele estrutura de forma exaustiva o inventário completo de **22 Issues abertas** e **9 Pull Requests ativas** no repositório `lfragoso93-web/sig-v2`, articulando-os sob regras estritas de integridade arquitetural, conservação financeira, segurança cibernética e certificação de dados reais.

### 1.1 Regras Fundamentais de Governança (GOV-01 a GOV-07)

Em conformidade com `docs/ISSUE_GOVERNANCE.md`:

- **GOV-01 (Hierarquia Única de Verdade)**: Nenhuma Issue ou PR pode competir como fonte de verdade paralela para o mesmo escopo de trabalho. Cada entrega deve possuir um vínculo canônico claro.
- **GOV-02 (Atomicidade de Defeitos)**: Qualquer bug reproduzível deve possuir uma Issue atômica e independente. Macroprojetos jamais devem mascarar ou encapsular bugs críticos P0/P1.
- **GOV-03 (Bloqueio Condicionado à Jornada Crítica)**: Features futuras ou melhorias não se convertem em bloqueadores de release (blockers) a menos que causem impacto material demonstrado na jornada crítica do usuário.
- **GOV-04 (Encerramento Baseado em Evidência)**: Issues concluídas ou integralmente absorvidas devem ser fechadas e rotuladas com comprovação de testes e artefatos de auditoria verificáveis.
- **GOV-05 (Reutilização de Evidências Certificadas)**: Evidências previamente certificadas e aprovadas devem ser reutilizadas; é vedado repetir operações destrutivas ou recertificações redundantes sem alteração de identidade.
- **GOV-06 (Sincronia entre Decisão e Documentação Viva)**: Documentação viva (`docs/`) e Issues do GitHub devem ser atualizadas no mesmo macrobloco em que qualquer decisão arquitetural ou de negócio for alterada.
- **GOV-07 (Saneamento Contínuo do Backlog)**: Manter a correlação formal entre o inventário de Issues abertas, branches ativas, PRs e contratos de código antes de qualquer marco de liberação em produção.

### 1.2 Os Sete Invariantes Arquiteturais e Operacionais Invioláveis

1. **Branching Governance**: O desenvolvimento ativo ocorre **exclusivamente na branch `stable-15jun`**. A branch `main` atua como trunk de releases promovidos e somente recebe código via Pull Requests auditadas com pipeline 100% verde. É estritamente proibido realizar commits diretos em `main`, force-push ou rebase em branches públicas.
2. **Identidade Exata de Release (Commit SHA)**: Releases, imagens Docker e certificações de dados reais são ancorados no hash completo de commit Git (`APP_COMMIT_SHA`). Tags flutuantes não conferem autoridade operacional.
3. **Certificação de Dados Reais Fail-Closed (`/ready`)**: O endpoint `/ready` do backend governa a prontidão para dados reais via autoridade DB-first (`real_data_certification_events`). Divergências de commit SHA, revisão Alembic, dataset hash (`pre-prod-backup.v3:sha256:...`) ou branch forçam resposta **HTTP 503 (Service Unavailable)**. Durante ciclos de desenvolvimento assistido, o sistema opera sob `/health=200` e diagnóstico `GO_ASSISTED`.
4. **Tolerância Zero a Desvios de Schema (Alembic Drift Gate)**: O gate automatizado `python -m app.governance.alembic_drift_gate` compara a metadata declarada do SQLAlchemy (`Base.metadata`) contra o schema gerado pelas migrações Alembic. Qualquer divergência não catalogada bloqueia a integração contínua (apenas o modelo transitório `goals` possui exceção documentada conforme #246/#57).
5. **Caminho de Leitura Financeira DB-First**: Páginas de patrimônio, rentabilidade, TWR, dividendos e IRPF consultam **exclusivamente** dados previamente normalizados e persistidos no PostgreSQL. Provedores de mercado externos jamais são chamados nos caminhos de leitura do usuário.
6. **Livro-Razão Canônico (`transactions`)**: A tabela `transactions` é o ledger canônico imutável de lançamentos. Lançamentos históricos jamais são mutados para absorver eventos corporativos; transformações são projetadas a partir de eventos oficiais da B3.
7. **Precedência Estrita de Dados de Mercado**: Para ativos listados brasileiros, a B3 (COTAHIST / endpoints estruturados) é a fonte primária oficial. A BRAPI atua exclusivamente como enriquecimento complementar de campos não cobertos pela B3. O Yahoo Finance é fallback estrito para emissores sem cobertura B3. Dados faltantes permanecem com status explícito (`HISTORY_END_UNAVAILABLE`), sendo expressamente vedado inventar cotações ou paridades artificiais.

---

## 2. Inventário Completo: Issues e Pull Requests

### 2.1 Inventário de Issues Abertas (22 Issues)

| Issue | Título | Trilha Governança | Severidade / Tipo | Status Atual / Evidência |
|---|---|---|---|---|
| **#408** | `[SECURITY] Neutralizar findings CodeQL de log injection #200–#203` | Segurança & Dependências | P1 / Segurança | **Resolvido em Código**: Alertas CodeQL #200–#203 confirmados como `fixed` em 19/10/2026. Pronta para encerramento formal após promoção. |
| **#370** | `[PRE-PROD][CORPORATE EVENTS] Reconciliar eventos materiais de AMOB3 e KLBN11 antes do GO` | Ações Corporativas & Carteira | P0 / Blocker Financeiro | **Em Aberto**: Schema `corporate_event_destination_legs` aplicado. Projetor multiativo implementado. Decisão de produto de 20/10/2026 fixa apuração de direito por carteira sem exigir nota de leilão. Eventos KLBN11 em `CONFLICT` fail-closed. |
| **#361** | `[AI] Camada de IA para análise explicável de carteiras e ativos` | Evolução Funcional | P3 / Feature | **Backlog Futuro**: Depende da estabilização da Analysis Engine determinística (#360) e do modelo de Metas (#246). |
| **#360** | `[ANALYSIS] Insights determinísticos por classe na Análise de Carteira` | Evolução Funcional | P2 / Feature | **Arquitetado**: Especificações de cálculos puros definidas; em espera da fase de métricas avançadas. |
| **#359** | `[FEATURE][TOOLS] Criar calculadora de rendimentos e calculadora de Renda Fixa` | Evolução Funcional | P2 / Feature | **Implementado / Pré-Deploy**: Frontend e backend implementados em Ferramentas. Testes determinísticos (4/4) e contratos (20/20) verdes. Pendente validação visual desktop/mobile. |
| **#358** | `[FEATURE][IMPORT][B3] Suportar arquivos da Área do Investidor B3 como adapter do import canônico` | Evolução Funcional | P2 / Feature | **Planejado**: Especificação de parsing de planilhas/extratos da B3 alinhada ao `transaction_write_service`. |
| **#357** | `[FEATURE][EXPORT] Exportar carteira e histórico de transações` | Evolução Funcional | P2 / Feature | **Planejado**: Exportador de lançamentos e posições em CSV/JSON via streams assíncronos. |
| **#356** | `[FEATURE][TRANSAÇÕES] Paginação independente por classe na tela de Transações` | Evolução Funcional | P2 / UX / Feature | **Planejado**: Paginação orientada a servidor por classe de ativo para evitar latência em carteiras extensas. |
| **#355** | `[FEATURE][RENDA FIXA] Introduzir taxonomia canônica de produtos de Renda Fixa` | Ações Corporativas & Carteira | P1 / Estrutural | **Implementado**: Contratos estruturados, chave estrangeira nullable, inferência transparente de contratos por termos e testes (13/13) aprovados. Pendente atualização de critério na Issue e validação visual. |
| **#353** | `[BUG][UX] Restaurar scroll no topo ao trocar de página` | Evolução Funcional | P2 / Bug UX | **Implementado**: Restauração de scroll global ativa via hook no React Router; pendente homologação visual integrada. |
| **#351** | `[EPIC][UX] SGI UI/UX V2 — design system, iconografia, navegação e responsividade` | Evolução Funcional | P2 / Epic UX | **Em Andamento**: Tokens TailwindCSS 4, iconografia Lucide e componentes modulares em consolidação progressiva. |
| **#293** | `[GOV] Sanitização e hierarquia do backlog antes da fase de testes` | Testes & Estabilização | P1 / Governança | **Fase Final (GOV-07)**: Inventário completo correlacionado. Fechamento condicionado à publicação deste Roadmap e harmonização de branches. |
| **#284** | `[OCI] Migração SGI v2 para Oracle Cloud Always Free` | Evolução Funcional | P3 / Infraestrutura | **Backlog OCI**: Arquitetura pronta em `docker-compose.oci.yml` com Cloudflare Tunnel; fora do caminho crítico local. |
| **#272** | `[ARCH] Contrair aliases físicos legados de corporate_events` | Ações Corporativas & Carteira | P2 / Dívida Técnica | **Bloqueado por Consumidores**: Campos legados ainda utilizados por fluxos de troca de ticker por carteira (`docs/CORPORATE_EVENTS_LEGACY_COLUMN_INVENTORY.md`). |
| **#253** | `[ADMIN] Central de Bootstrap por etapas para SuperAdmin` | Evolução Funcional | P2 / Admin | **Backlog Admin**: Interface com steps para importação guiada COTAHIST / SELIC / CDI. |
| **#246** | `[ARCH] Macroprojeto Metas + Análise de Carteira` | Evolução Funcional | P2 / Arquitetura | **Backlog Estrutural**: Alinhamento de schema entre `goals` e o motor financeiro; exceção temporária no drift gate. |
| **#149** | `[HIGH] Concluir TWR diário dedicado de Tesouro Direto e Renda Fixa` | Ações Corporativas & Carteira | P1 / Métricas | **Quase Concluído**: Algoritmo de TWR implementado; pendente teste de conciliação por lote custodiado e apuração fiscal. |
| **#130** | `[HIGH] Evolução da integração brapi v2 e enriquecimento de ativos` | Evolução Funcional | P2 / Provedores | **Especificado**: Enriquecimento secundário com respeito à autoridade B3 e fallbacks fail-closed. |
| **#127** | `Arquitetura de provedores de dados configuráveis pelo Superadmin` | Evolução Funcional | P2 / Segurança / Admin | **Especificado**: Painel administrativo para gestão de chaves de API e prioridade de sincronização. |
| **#97** | `Auth: implementar login com Google OAuth` | Evolução Funcional | P2 / Auth | **Planejado**: Provedor OpenID Connect integrado ao JWT seguro do FastAPI. |
| **#90** | `Roadmap: refinar UX da página Patrimônio com layout em cards` | Evolução Funcional | P2 / UX | **Planejado**: Layout responsivo em grid com visualização em cards de distribuição de patrimônio. |
| **#58** | `🔍 Sprint 9 — Janela Global do Ativo` | Evolução Funcional | P2 / Feature | **Parcialmente Concluído**: Modal global implementado; chamada antiga de proventos corrigida para contrato canônico. |

### 2.2 Inventário de Pull Requests Abertas (9 PRs)

| PR | Título | Autor | Branch Base ← Head | Status Checks | Ação Requerida de Governança |
|---|---|---|---|---|---|
| **#434** | `chore: promote stable-15jun baseline to main` | `lfragoso93-web` | `main` ← `stable-15jun` | **14/14 PASS** | **Merge Imediato**: Promove a baseline consolidada, resolve o falso positivo de Gitleaks na `main`, atualiza CodeQL e scans Trivy. |
| **#433** | `chore(security): allowlist historical Gitleaks false positive` | `lfragoso93-web` | `main` ← `codex/gitleaks-historical-roadmap-fingerprint` | **8/8 PASS** | **Absorvida pelo PR #434**: Pode ser fechada como supersedida assim que a PR #434 for integrada. |
| **#432** | `build(deps-dev): bump @tailwindcss/postcss from 4.3.2 to 4.3.3 in /frontend` | Dependabot | `main` ← `dependabot/npm_and_yarn/frontend/tailwindcss/postcss-4.3.3` | **8/8 PASS** | **Rebase / Merge**: Atualizar target para `stable-15jun` ou mesclar pós-#434. |
| **#431** | `build(deps): bump lucide-react from 1.35.0 to 1.58.0 in /frontend` | Dependabot | `main` ← `dependabot/npm_and_yarn/frontend/lucide-react-1.58.0` | **8/8 PASS** | **Rebase / Merge**: Integração segura na trilha de frontend. |
| **#430** | `build(deps-dev): bump the build-tools group in /frontend with 5 updates` | Dependabot | `main` ← `dependabot/npm_and_yarn/frontend/build-tools-6c3374a135` | **8/8 PASS** | **Rebase / Merge**: Alinhamento com peer dependencies de `typescript-eslint` aprovado em CI. |
| **#429** | `build(deps): bump @tanstack/react-query from 5.104.1 to 5.104.3 in /frontend` | Dependabot | `main` ← `dependabot/npm_and_yarn/frontend/tanstack-a4b08ae148` | **8/8 PASS** | **Rebase / Merge**: Patch bump sem impacto de API. |
| **#428** | `build(deps): bump the react-stack group in /frontend with 5 updates` | Dependabot | `main` ← `dependabot/npm_and_yarn/frontend/react-stack-ab84cf3f03` | **8/8 PASS** | **Rebase / Merge**: Grupo React core atualizado e verificado. |
| **#427** | `build(deps): bump the sqlalchemy-stack group in /backend with 2 updates` | Dependabot | `main` ← `dependabot/pip/backend/sqlalchemy-stack-2d3ae82822` | **8/8 PASS** | **Rebase / Merge**: Atualização de SQLAlchemy para 2.1.4 com contrato runtime validado. |
| **#426** | `build(deps): bump the fastapi-stack group in /backend with 2 updates` | Dependabot | `main` ← `dependabot/pip/backend/fastapi-stack-93f74109ca` | **8/8 PASS** | **Rebase / Merge**: FastAPI stack atualizada sem quebra de endpoints. |

---

## 3. As Quatro Trilhas Governança de Desenvolvimento

```
+---------------------------------------------------------------------------------------------------+
|                                      SGI v2 DEVELOPMENT TRACKS                                     |
+---------------------------------+---------------------------------+-------------------------------+
| Trilha 1: Segurança & Dep.      | Trilha 2: Testes & Estabiliz.   | Trilha 3: Corp. & Carteira    |
| - Dependabot PRs #426–#432      | - Alembic Drift Gate Fix        | - Issue #370 (KLBN11/AMOB3)   |
| - PR #433 / Gitleaks allowlist  | - Vitest Suite CI Integration   | - Multi-leg Schema Migration  |
| - Issue #408 (CodeQL closure)   | - Docker Desktop Stack Health   | - Issue #355 (Renda Fixa)     |
| - Trivy FS & Image Scans        | - Certificação #384 (/ready)    | - Issue #149 (TWR Tesouro/RF) |
| - Target Branch Alignment       | - Architecture Doctor Gates     | - Issue #272 (Schema Cleanup) |
+---------------------------------+---------------------------------+-------------------------------+
|                                  Trilha 4: Evolução Funcional                                     |
| - Ferramentas / Calculadoras (#359)                 - UI/UX V2 Design System (#351, #90, #58)     |
| - Importador B3 / Exportador (#358, #357)           - Análise Determinística & Metas (#246, #360) |
| - Paginação / Scroll (#356, #353)                   - Camada IA Explicável & Cloud OCI (#361, #284)|
+---------------------------------------------------------------------------------------------------+
```

### Trilha 1: Segurança & Dependências

#### 1.1 Alinhamento do Dependabot e Correção de Target Branch
- **Diagnóstico**: O arquivo `.github/dependabot.yml` omitiu a diretiva `target-branch: "stable-15jun"`, fazendo com que todas as PRs automáticas (#426–#432) fossem abertas contra a branch padrão (`main`). Como `stable-15jun` é o branch de desenvolvimento ativo e está commits à frente de `main`, a tentativa de merge manual ou squash contra `main` gerou conflitos de histórico.
- **Ação Técnica Requerida**:
  1. Configurar explicitamente `target-branch: "stable-15jun"` nos blocos `pip` e `npm` de `.github/dependabot.yml`.
  2. Integrar a PR #434 na branch `main`, nivelando a base remota com `stable-15jun`.
  3. Portar/rebasear os 7 pacotes de dependências verdes (#426–#432) diretamente em `stable-15jun`.

#### 1.2 Neutralização de Falsos Positivos do Gitleaks (PR #433 / PR #434)
- **Diagnóstico**: A execução de CI manual em `main` (Run 39256023327) falhou na etapa `Secret scan – Gitleaks` com o erro:
  `WRN leaks found: 1 | Fingerprint: 1d245ff76ecc4fcf164073c8a731809cb93d2dc9:ROADMAP.md:generic-api-key:423`.
  Trata-se de uma string de documentação histórica contendo um exemplo ilustrativo de chave de API.
- **Resolução**: A fingerprint foi devidamente allowlisted em `.gitleaksignore` na branch `stable-15jun` e incorporada na PR #434. A promoção da PR #434 elimina permanentemente a falha na `main`.

#### 1.3 Protocolo de Fechamento Formal da Issue #408 (CodeQL Log Injection)
- **Diagnóstico**: A Issue #408 reportou alertas CodeQL #200 a #203 referentes a potencial injeção de log em `portfolio_service.py` e `treasury_catalog_service.py`. As correções foram introduzidas pelas PRs #413 e #419.
- **Evidência Definitiva**: A consulta direta à API de Code Scanning do GitHub (`gh api /repos/lfragoso93-web/sig-v2/code-scanning/alerts`) confirmou que os quatro alertas foram marcados como `fixed` na execução deep scan de 19/10/2026 às 13:20:36Z.
- **Protocolo de Conclusão**:
  1. Verificar a promoção do código saneado para `main` via PR #434.
  2. Adicionar comentário formal na Issue #408 anexando os IDs de alerta (#200-#203) e os timestamps de correção.
  3. Fechar a Issue #408 com status `completed`.

#### 1.4 Gates de Segurança Contínua (Trivy, CodeQL e Audits)
- O pipeline de CI (`.github/workflows/ci.yml`) e o deep scan (`.github/workflows/security-deep-scan.yml`) executam:
  - Trivy filesystem scan (vulnerabilidades em pacotes OS e bibliotecas).
  - Trivy image scan para as imagens `sig-v2-backend` e `sig-v2-frontend`.
  - Hadolint para linter de Dockerfiles.
  - `pip-audit` e `npm audit` para análise de vulnerabilidades em dependências Python e Node.
  - Alertas com severidade `CRITICAL` ou `HIGH` são bloqueadores de certificação.

---

### Trilha 2: Testes & Estabilização

#### 2.1 Remediação do Alembic Metadata Drift Gate
- **Diagnóstico**: A execução do comando `python -m app.governance.alembic_drift_gate` no backend falhou com código 1 devido à seguinte operação autogerada:
  `DropIndexOp table=corporate_event_destination_legs index_name=ix_corp_event_destination_leg_asset`.
- **Causa Raiz**: A migration `20261019_corporate_event_destination_legs.py` criou o índice `ix_corp_event_destination_leg_asset` na coluna `destination_asset_id`. Contudo, no modelo SQLAlchemy correspondente (`CorporateEventDestinationLeg` em `backend/app/models/corporate_event.py`, linha 202), a definição da coluna omitiu o argumento `index=True`. O Alembic autogenerate interpreta a ausência do índice no modelo como uma remoção intencional. Como `corporate_event_destination_legs` não faz parte de `ALLOWED_DRIFT_TABLES` (que isola estritamente `goals`), o gate falha fechado.
- **Solução Imediata**: Adicionar `index=True` em `CorporateEventDestinationLeg.destination_asset_id` no modelo ORM, reestabelecendo a paridade perfeita entre modelo e banco de dados.

#### 2.2 Integração da Suíte Completa Vitest na CI
- **Diagnóstico**: O frontend possui **57 arquivos de teste Vitest** em `frontend/src/**/__tests__/`. Contudo, o workflow de CI (`.github/workflows/ci.yml`, linhas 110-136) executa apenas `npm run lint`, `npm run typecheck` e `npm run build`, omitindo completamente a execução dos testes unitários e de componentes (`vitest run`).
- **Ação Técnica Requerida**: Adicionar o step `Run frontend unit tests` executando `npm test -- run` logo após o typecheck no workflow de CI, garantindo 100% de cobertura automatizada no GitHub Actions.

#### 2.3 Estabilidade e Diagnóstico do Runtime Docker Desktop
- **Estado Operacional**: A stack `sig-v2` no Docker Desktop está totalmente operacional e saudável (`sig-v2-backend-1`: healthy, `sig-v2-db-1`: healthy, `sig-v2-redis-1`: healthy, `sig-v2-frontend-1`: running, `sig-v2-cloudflared-1`: running com 4 túneis QUIC ativos).
- **Roteamento e Portas**: Conforme `docker-compose.oci.yml`, as portas do host estão isoladas (`ports: !reset []`), operando com tráfego seguro através do Cloudflare Tunnel apontado para `sgi.lfconsultoria.dpdns.org`.
- **Manutenção de Volumes**: Proibição estrita de comandos destrutivos (`docker compose down -v`, deleção de volumes ou remoção de contêineres sem backup prévio).

#### 2.4 Fluxo de Certificação para Dados Reais (#384 / `sgi-certification`)
- **Regra de Prontidão**: A promoção de certificação de dados reais é uma ação operacional formal e append-only governada pelo script `app.cli.real_data_certification`.
- **Condições de Promoção**:
  1. Suítes completas de testes de backend e frontend com 100% de aprovação.
  2. Architecture Doctor aprovado (exit code 0 nos 6 checks estáticos).
  3. Alembic drift gate 100% aprovado (exit code 0).
  4. Extração de hash do dataset via `app.cli.real_data_dataset_identity` sobre o backup canônico `pre-prod-backup.v3`.
  5. Dry-run sem escritas para extração da chave de evento e confirmação.
  6. Execução protegida com confirmação explícita (`--execute --confirmation <hash>`).

---

### Trilha 3: Ações Corporativas & Carteira

#### 3.1 Resolução da Issue #370 (Ações Corporativas Complexas, AMOB3 e KLBN11)
- **Contexto e Histórico**: Eventos de bonificação e cisão com leilão de frações (destacadamente KLBN11 e AMOB3) exigem reconciliação matemática precisa para conservação de custo fiscal (`custo_origem = soma_custos_destino`).
- **Decisão de Produto Vigente (20/10/2026)**:
  - Para bonificações com frações leiloadas, o **direito bruto do usuário** deve ser calculado pelo SGI a partir da quantidade elegível na carteira na data-base oficial, da proporção do emissor e do preço oficial publicado de liquidação do leilão.
  - O valor apurado é exibido na carteira sob status **"A confirmar"** (`PENDING_SETTLEMENT`).
  - Não é exigido o envio prévio de nota de corretagem individual para calcular o direito derivado bruto.
  - O crédito efetivo em caixa só é confirmado quando houver lançamento de provento ou extrato do custodiante comprovando o pagamento financeiro.
- **Os Três Gates Técnicos de #370**:
  1. *Gate 1 (Direito Derivado por Carteira)*: Apuração e exibição do direito fracionário em Patrimônio como ativo transitório.
  2. *Gate 2 (Integração na Timeline Financeira)*: Transformação multiativo integrada em posições, custo médio, cálculo de resultado realizado, snapshots históricos, TWR e IRPF.
  3. *Gate 3 (Confirmação de Liquidação em Caixa)*: Liquidação de frações com registro de provento financeiro apenas sob evidência do custodiante.
- **Estado de KLBN11**: Mantido em status `CONFLICT` fail-closed até que o Gate 2 e a confirmação de frações sejam completamente incorporados.

#### 3.2 Persistência Canônica de Pernas Multi-Ativo (`corporate_event_destination_legs`)
- A tabela `corporate_event_destination_legs` (revisão Alembic `20261019_corp_event_legs`) permite múltiplos ativos de destino com fatores individuais (`allocation_ratio`) e fatores monetários.
- A persistência é atômica, aditiva e idempotente, garantindo conservação de custo estrita.

#### 3.3 Taxonomia Canônica de Renda Fixa (Issue #355)
- **Progresso**: Modelagem de produtos de Renda Fixa concluída com campos estruturados (`indexer`, `interest_rate`, `maturity_date`, `liquidity_type`), associação transparente por termos equivalentes dentro da mesma carteira e remoção de seletores manuais redundantes no formulário.
- **Próximos Passos**: Atualizar o corpo remoto da Issue #355 para refletir a substituição do seletor explícito de contrato pela associação automática por termos, e concluir a homologação visual.

#### 3.4 TWR Diário Dedicado para Renda Fixa e Tesouro Direto (Issue #149)
- Implementação de métrica TWR contínua para ativos prefixados e indexados à inflação/CDI. Conexão com regras de apuração fiscal por lote (IRRF regressivo).

#### 3.5 Contração de Aliases Físicos Legados de Eventos Corporativos (Issue #272)
- Remoção definitiva de colunas históricas legadas na tabela `corporate_events`.
- Ação permanece condicionada à migração dos consumidores ativos mapeados em `docs/CORPORATE_EVENTS_LEGACY_COLUMN_INVENTORY.md` (especialmente trocas de ticker na carteira).

---

### Trilha 4: Evolução Funcional

#### 4.1 Ferramentas e Calculadoras Financeiras (Issue #359)
- **Calculadora de Rendimentos**: Comparação dinâmica entre investimentos (CDB, LCI/LCA, Tesouro Direto, Fundos DI) considerando tabelas regressivas de IR e inflação implícita.
- **Simulador de Renda Fixa**: Projeção de fluxo de caixa futuro e amortizações.
- **Status**: Backend e Frontend integrados sob o menu **Ferramentas**; aguarda sessão de validação visual desktop/mobile.

#### 4.2 Portabilidade de Dados: Importação B3 e Exportação (Issues #358 e #357)
- **#358 (Importador Área do Investidor B3)**: Adapter de leitura para extratos consolidados da B3 (arquivos Excel/CSV da Área do Investidor), traduzindo-os para comandos canônicos em `transaction_write_service`.
- **#357 (Exportação de Carteira e Transações)**: Download estruturado em CSV e JSON com hashing de integridade e metadados fiscais.

#### 4.3 Experiência do Usuário — UI/UX V2 Design System (Issues #351, #90, #58, #353, #356)
- **#351 (UI/UX V2)**: Consolidação de tokens visuais em TailwindCSS 4, padrões de acessibilidade (ARIA labels, contraste, foco por teclado) e tipografia padronizada.
- **#90 (Cards de Patrimônio)**: Exibição moderna da distribuição patrimonial em cards por classe de ativo.
- **#58 (Modal Global de Ativo)**: Painel detalhado de ativo com cotações históricas, proventos recebidos, posição na carteira e eventos corporativos pendentes.
- **#353 (Restauração de Scroll)**: Manutenção da rolagem ao topo ao navegar entre rotas.
- **#356 (Paginação Independente de Transações)**: Controle de paginação server-side por classe na listagem de transações.

#### 4.4 Análise Avançada, Metas e Inteligência Artificial (Issues #246, #360, #361)
- **#246 (Metas e Análise de Carteira)**: Macroprojeto estrutural que integra objetivos financeiros (aposentadoria, reserva de emergência, projetos) à projeção patrimonial.
- **#360 (Analysis Engine Determinística)**: Motor puramente analítico para geração de insights matemáticos sobre diversificação, volatilidade, drawdowns e concentração.
- **#361 (Camada de IA Explicável)**: Agente de IA para geração de relatórios explicativos em linguagem natural baseados estritamente nos dados auditados gerados pela Analysis Engine (#360).

#### 4.5 Autenticação, Provedores e Infraestrutura Cloud (Issues #97, #127, #130, #253, #284)
- **#97 (Google OAuth)**: Autenticação federada social mantendo segurança multi-tenant e RBAC.
- **#127 & #130 (Provedores Configuráveis e BRAPI v2)**: Gestão de quotas, chaves de API e enriquecimento controlado de ativos.
- **#253 (Central de Bootstrap Superadmin)**: Painel administrativo para carga inicial e sincronização sob demanda.
- **#284 (Migração Oracle Cloud Always Free)**: Backlog de infraestrutura para deployment em OCI, preservando as diretrizes de hardening do `docker-compose.oci.yml`.

---

## 4. Matriz de Priorização (Impacto vs Risco / Complexidade)

Cada item catalogado foi classificado segundo os critérios:
- **Impacto**: Avaliação do benefício direto para integridade contábil, segurança, conformidade e experiência do usuário (Alto, Médio, Baixo).
- **Risco / Complexidade**: Dificuldade técnica de implementação, risco de regressão financeira ou quebra de invariantes (Alto, Médio, Baixo).
- **Prioridade Governança**:
  - **P0 (Blocker / Imediato)**: Bloqueia estabilidade de CI, conformidade de schema ou acurácia patrimonial crítica.
  - **P1 (Crítico / Curto Prazo)**: Correções de integridade, testes de segurança e dívidas contábeis centrais.
  - **P2 (Evolução / Médio Prazo)**: Novas funcionalidades de produto, melhorias visuais e ferramentas.
  - **P3 (Backlog Futuro / Longo Prazo)**: Migrações de nuvem e inteligência artificial avançada.

| ID | Item / Título | Trilha | Impacto | Risco / Compl. | Prioridade | Fase Alvo |
|---|---|---|---|---|---|---|
| **PR #434** | Promoção da baseline stable-15jun para main | Segurança & Dep. | Alto | Baixo | **P0** | Fase 1 |
| **Fix Drift** | Correção do índice no modelo CorporateEventDestinationLeg | Testes & Estab. | Alto | Baixo | **P0** | Fase 1 |
| **PR #433** | Allowlist da fingerprint histórica Gitleaks | Segurança & Dep. | Médio | Baixo | **P0** | Fase 1 |
| **Issue #408** | Fechamento formal de log injection CodeQL #200–#203 | Segurança & Dep. | Alto | Baixo | **P1** | Fase 1 |
| **Issue #293** | Sanitização do backlog GOV-07 e hierarquia | Testes & Estab. | Alto | Baixo | **P1** | Fase 1 |
| **Vitest CI** | Integração dos testes unitários de frontend na CI | Testes & Estab. | Alto | Baixo | **P1** | Fase 1 |
| **Dep Target** | Alinhamento de target-branch no Dependabot | Segurança & Dep. | Médio | Baixo | **P1** | Fase 1 |
| **PR #427** | Bump do SQLAlchemy stack para 2.1.4 | Segurança & Dep. | Médio | Médio | **P1** | Fase 1 |
| **PR #430** | Bump do build-tools stack frontend (TS 6.0.3) | Segurança & Dep. | Médio | Médio | **P1** | Fase 1 |
| **PR #426** | Bump do FastAPI stack no backend | Segurança & Dep. | Médio | Baixo | **P1** | Fase 1 |
| **PR #428** | Bump do React stack no frontend | Segurança & Dep. | Médio | Baixo | **P1** | Fase 1 |
| **PR #429** | Bump do TanStack React Query | Segurança & Dep. | Médio | Baixo | **P1** | Fase 1 |
| **PR #431** | Bump de Lucide React | Segurança & Dep. | Baixo | Baixo | **P1** | Fase 1 |
| **PR #432** | Bump de PostCSS Tailwind | Segurança & Dep. | Baixo | Baixo | **P1** | Fase 1 |
| **Issue #370** | Reconciliação AMOB3 e KLBN11 (Pernas multiativo) | Corp. & Carteira | Alto | Alto | **P0** | Fase 2 |
| **Issue #355** | Conclusão e homologação da Taxonomia de Renda Fixa | Corp. & Carteira | Alto | Médio | **P1** | Fase 2 |
| **Issue #149** | TWR dedicado de Renda Fixa e Tesouro Direto | Corp. & Carteira | Alto | Médio | **P1** | Fase 2 |
| **Issue #272** | Contração física de aliases de corporate_events | Corp. & Carteira | Médio | Alto | **P2** | Fase 2 |
| **Issue #359** | Calculadora de rendimentos e simulador RF | Evolução Funcional| Alto | Médio | **P1** | Fase 3 |
| **Issue #358** | Adapter da Área do Investidor B3 | Evolução Funcional| Alto | Médio | **P2** | Fase 3 |
| **Issue #357** | Exportação de carteira e histórico de transações | Evolução Funcional| Médio | Baixo | **P2** | Fase 3 |
| **Issue #356** | Paginação por classe em Transações | Evolução Funcional| Médio | Baixo | **P2** | Fase 3 |
| **Issue #353** | Restauração de scroll global na navegação | Evolução Funcional| Médio | Baixo | **P2** | Fase 3 |
| **Issue #351** | SGI UI/UX V2 Design System | Evolução Funcional| Alto | Médio | **P2** | Fase 3 |
| **Issue #90** | Refinamento UX de Patrimônio em cards | Evolução Funcional| Médio | Baixo | **P2** | Fase 3 |
| **Issue #58** | Janela Global do Ativo (Modal Global) | Evolução Funcional| Médio | Baixo | **P2** | Fase 3 |
| **Issue #97** | Autenticação Google OAuth | Evolução Funcional| Médio | Médio | **P2** | Fase 3 |
| **Issue #127** | Provedores configuráveis pelo Superadmin | Evolução Funcional| Médio | Médio | **P2** | Fase 3 |
| **Issue #130** | Evolução da integração BRAPI v2 | Evolução Funcional| Médio | Médio | **P2** | Fase 3 |
| **Issue #253** | Central de Bootstrap por etapas | Evolução Funcional| Médio | Médio | **P2** | Fase 3 |
| **Issue #246** | Macroprojeto Metas + Análise de Carteira | Evolução Funcional| Alto | Alto | **P2** | Fase 4 |
| **Issue #360** | Analysis Engine Determinística | Evolução Funcional| Alto | Alto | **P2** | Fase 4 |
| **Issue #361** | Camada de IA para análise explicável | Evolução Funcional| Médio | Alto | **P3** | Fase 4 |
| **Issue #284** | Migração SGI v2 para Oracle Cloud (OCI) | Evolução Funcional| Médio | Médio | **P3** | Fase 4 |

---

## 5. Fases de Liberação por Milestones

### Fase 1: Estabilização Imediata e Governança de Segurança (Imediato)

*Objetivo Central*: Sincronizar branches base, zerar dívidas de CI, garantir passagem sem falhas de todos os gates automatizados e alinhar a gestão de dependências.

- **Entregas Principais**:
  1. Realizar merge da PR #434 na branch `main`, sincronizando 41 commits acumulados da `stable-15jun`.
  2. Fechar PR #433 como supersedida por #434.
  3. Atualizar `.github/dependabot.yml` com `target-branch: "stable-15jun"`.
  4. Realizar o merge sequencial controlado das PRs de dependências (#426–#432) com validação de build em `stable-15jun`.
  5. Fechar formalmente a Issue #408 via comentário comprovando os 4 alertas CodeQL resolvidos.
  6. Corrigir a falta de `index=True` no modelo `CorporateEventDestinationLeg` (`backend/app/models/corporate_event.py:202`) e comprovar execução com sucesso do gate `app.governance.alembic_drift_gate` (exit code 0).
  7. Adicionar o step de execução do Vitest (`npm test -- run`) no workflow `.github/workflows/ci.yml`.
  8. Concluir o alinhamento de GOV-07 e encerrar formalmente a Issue #293.
- **Critérios de Saída (Exit Criteria)**:
  - Branch `main` com CI 100% verde (incluindo Gitleaks e Trivy).
  - Branch `stable-15jun` sem pendências de dependências ou desvios de schema no Alembic drift gate.
  - Zero alertas abertos em CodeQL, Dependabot e Secret Scanning.

---

### Fase 2: Correção Financeira Pré-Produção e Integridade Contábil (Curto Prazo)

*Objetivo Central*: Resolver pendências contábeis de eventos corporativos complexos, fechar a taxonomia de Renda Fixa e validar métricas diárias de rentabilidade.

- **Entregas Principais**:
  1. **Issue #370 (Ações Corporativas Complexas)**:
     - Homologar o cálculo do direito derivado bruto por carteira para frações leiloadas (exibição como "A confirmar" em Patrimônio).
     - Concluir a integração da projeção multiativo nas posições, custo médio, resultado realizado, snapshots históricos, TWR e IRPF.
     - Preservar status `CONFLICT` fail-closed para KLBN11 até comprovação do evento pelo custodiante.
     - Atualizar critérios remotos na Issue #370 desvinculando o cálculo do direito bruto da exigência de nota individual prévia.
  2. **Issue #355 (Taxonomia Canônica de Renda Fixa)**:
     - Atualizar o corpo remoto da Issue desvinculando o seletor manual antigo em favor da inferência por termos equivalentes.
     - Realizar a validação visual responsiva (desktop/mobile) dos formulários e tabelas de Renda Fixa.
     - Encerrar formalmente a Issue #355 com evidência de testes e migrações.
  3. **Issue #149 (TWR Diário Dedicado)**:
     - Finalizar testes de conciliação por lote custodiado para Renda Fixa e Tesouro Direto.
     - Fechar Issue #149 com comprovação matemática de ausência de distorção de rentabilidade por influxo de caixa.
  4. **Issue #272 (Contração de Aliases Físicos de Corporate Events)**:
     - Migrar os leitores de troca de ticker para a nova tabela canônica e aplicar a migration de descontinuação de colunas legadas.
- **Critérios de Saída (Exit Criteria)**:
  - Fechamento formal das Issues #370, #355, #149 e #272.
  - Execução de ciclo formal de certificação de dados reais (#384) promovendo o novo runtime SHA com emissão do artefato `sgi-certification.v1` e endpoint `/ready` retornando HTTP 200.

---

### Fase 3: Funcionalidades Centrais, Portabilidade e Experiência do Usuário (Médio Prazo)

*Objetivo Central*: Entregar ferramentas avançadas de cálculo, importadores/exportadores canônicos e consolidar o Design System V2.

- **Entregas Principais**:
  1. **Issue #359 (Ferramentas & Calculadoras)**:
     - Homologar sessões visuais do comparador de rendimentos e simulador de renda fixa.
     - Lançar módulo de Ferramentas oficialmente para os usuários finais.
  2. **Issues #358 e #357 (Portabilidade de Dados)**:
     - Implementar o importador da Área do Investidor B3 conectando ao `transaction_write_service`.
     - Implementar exportação segura de lançamentos e posições em CSV/JSON.
  3. **Issues #351, #90, #58, #353, #356 (UI/UX V2)**:
     - Aplicar padronização completa de tokens TailwindCSS 4 e acessibilidade.
     - Implementar cards na página de Patrimônio (#90) e paginação por classe em Transações (#356).
     - Homologar a Janela Global do Ativo (#58) e restauração de scroll (#353).
  4. **Issues #97, #127, #130, #253 (Auth, Provedores e Admin)**:
     - Implementar Google OAuth (#97).
     - Concluir painel de controle de provedores e central de bootstrap do SuperAdmin.
- **Critérios de Saída (Exit Criteria)**:
  - Módulo Ferramentas e Importador B3 operacionais em ambiente de teste de usuário com feedback positivo.
  - Fechamento das Issues de UX e ferramentas.

---

### Fase 4: Análise Avançada, Inteligência Artificial e Infraestrutura Cloud (Longo Prazo)

*Objetivo Central*: Implementar a esteira determinística de metas e análise de carteira, adicionar inteligência artificial explicável e habilitar migração para a nuvem.

- **Entregas Principais**:
  1. **Issues #246 e #360 (Metas & Analysis Engine Determinística)**:
     - Refatorar o schema de `goals`, alinhando os tipos de dados e removendo a tolerância temporária do Alembic drift gate.
     - Implementar a Analysis Engine determinística com métricas de Sharpe, Sortino, drawdowns e correlações entre ativos.
  2. **Issue #361 (Camada de IA Explicável)**:
     - Construir o serviço de IA para geração de diagnósticos explicáveis e contextuais, consumindo exclusivamente os outputs validados da Analysis Engine.
  3. **Issue #284 (Migração OCI Always Free)**:
     - Executar o runbook de migração para instâncias Oracle Cloud Infrastructure Always Free utilizando Docker Compose OCI e Cloudflare Tunnel.
- **Critérios de Saída (Exit Criteria)**:
  - Conclusão da esteira de Metas e Análise de Carteira com zero drift no Alembic drift gate.
  - Deployment automatizado e monitorado em infraestrutura de nuvem com alta disponibilidade.

---

## 6. Governança de Release, Gates e Protocolos Operacionais

### 6.1 Fluxo de Ramificação e Promoção (Branching & PR Flow)

```
[Desenvolvimento Ativo] ──> Branch: stable-15jun (commits atômicos)
                                      │
                                      ▼
                        [Validação Local & Compose]
                        - pytest backend (2.400+ testes)
                        - vitest frontend (57 suítes)
                        - python -m app.doctor --all-static
                        - python -m app.governance.alembic_drift_gate
                                      │
                                      ▼
                        [Pull Request Auditada] ──> Base: main
                        - Pipeline CI completo (14 jobs)
                        - Scans de Segurança (CodeQL + Trivy + Gitleaks)
                                      │
                                      ▼
                        [Branch: main Promovida]
                                      │
                                      ▼
                        [Certificação de Dados Reais (#384)]
                        - Backup consistente v3
                        - Prova imutável (sgi-certification.v1)
                        - /ready HTTP 200 (GO)
```

1. **Ciclo de Desenvolvimento**:
   - Todo código novo deve ser commitado exclusivamente em `stable-15jun`.
   - Não iniciar nova funcionalidade com a árvore de trabalho suja ou contendo arquivos não rastreados acidentais.
2. **Convenção de Commits**:
   - Padrão **Conventional Commits** estrito (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `build:`).
   - Commits devem ser pequenos, autônomos e acompanhados de seus testes e atualizações de documentação no mesmo commit.
3. **Promoção para Trunk (`main`)**:
   - Apenas macroblocos estáveis, testados e com documentação aprovada são promovidos via PR formal de `stable-15jun` para `main`.
   - É proibido realizar merge em `main` com jobs de CI falhando ou ignorados.

---

### 6.2 Protocolo de Certificação para Dados Reais (`sgi-certification`)

Em estrita consonância com `sgi-certification/SKILL.md` e `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`:

1. **Imutabilidade e Exatidão**: A certificação vincula de forma inseparável:
   - Branch: `stable-15jun`
   - Commit Git SHA: Hash SHA-1 completo de 40 caracteres.
   - Revisão Alembic: Identificador exato da migration head.
   - Dataset Reference: `pre-prod-backup.v3:sha256:<digest>` gerado via `app.cli.real_data_dataset_identity`.
2. **Fluxo Obrigatório em 6 Etapas**:
   - *Passo 1*: Auditoria read-only de status de serviços, árvore Git, migrações e contêineres.
   - *Passo 2*: Geração de prova sumária (`app.cli.certification_proof`) que verifica suíte de testes aprovada e Architecture Doctor verde.
   - *Passo 3*: Execução da CLI de certificação em modo **dry-run** (sem a flag `--execute`):
     ```powershell
     python -m app.cli.real_data_certification --action promote --dry-run
     ```
   - *Passo 4*: Verificação do plano estruturado emitido em JSON, chave de evento (`event_key`) e hash de confirmação (`confirmation`).
   - *Passo 5*: Solicitação de autorização expressa do usuário humano para o hash exato.
   - *Passo 6*: Execução atômica da escrita de certificação com validação da confirmação:
     ```powershell
     python -m app.cli.real_data_certification --action promote --execute --confirmation <hash>
     ```
3. **Comportamento do Endpoint `/ready`**:
   - Valida o último evento persistido na tabela `real_data_certification_events`.
   - Se qualquer um dos quatro componentes de identidade divergir, responde **HTTP 503 (identity_mismatch)**.
   - Responde **HTTP 200 OK** (`ready_for_real_data: true`) única e exclusivamente quando a identidade runtime for idêntica à do evento promovido.

---

### 6.3 Gate de Metadados e Drift de Banco de Dados (Alembic Drift Gate)

O script `backend/app/governance/alembic_drift_gate.py` garante a convergência formal entre a camada de código e o schema relacional:

- **Mecanismo de Execução**: Cria um schema temporário de teste, aplica todas as migrações Alembic até a head atual (`alembic upgrade head`) e executa o `autogenerate` comparando o estado resultante com `Base.metadata`.
- **Política de Falha Fechada**: Se o autogenerate produzir qualquer operação de DDL (`DropIndexOp`, `AddColumnOp`, `AlterColumnOp`, etc.) para tabelas que não estejam na lista de exceções explícitas (`ALLOWED_DRIFT_TABLES = {"goals"}`), o gate imprime a lista de operações divergentes e aborta o pipeline com **exit code 1**.
- **Regra de Manutenção**: Nenhuma alteração em modelos ORM do SQLAlchemy pode ser aceita sem sua correspondente migração Alembic revisada.

---

### 6.4 Gates do Architecture Doctor

O consolidor de regras arquiteturais `backend/app/doctor` implementa a verificação contínua de 15 invariantes estruturais (SGI001 a SGI015):

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
```

- **SGI002**: Protocolo de relógio injetável (`Clock` timezone-aware, rejeição de datetime naive).
- **SGI004**: Configuração fail-closed de startup sem vazamento de senhas em logs.
- **SGI005**: Autorização e isolamento rigoroso via `PortfolioAccessContext`.
- **SGI007**: Proteção anti-regressão N+1 em leituras críticas via `assert_max_queries`.
- **SGI009**: Leases distribuídas e locks seguros no Redis com fail-closed em caso de queda.
- **SGI012**: Contratos de conformidade de skills e documentação de governança.

O runner retorna `exit_code: 0` para aprovação unânime, `exit_code: 1` para falha em regra mandatória e `exit_code: 2` para erro de execução interna, bloqueando sumariamente qualquer candidato à certificação.

---

## 7. Rastreabilidade e Condições de Invalidação

### 7.1 Matriz de Rastreabilidade com Documentos Vivos do Repositório

| Documento de Referência | Escopo de Governança | Status e Relação com Este Roadmap |
|---|---|---|
| `docs/ISSUE_GOVERNANCE.md` | Governança geral de Issues e histórico de snapshots | Documento pai: estabelece as regras GOV-01 a GOV-07 respeitadas neste Roadmap. |
| `ROADMAP.md` | Roadmap executivo de produto e diário de bordo | Documento histórico: este roadmap complementa e aprofunda os critérios técnicos formais. |
| `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` | Runbook operacional de certificação de dados reais | Procedimento padrão para as fases pós-build e liberação de dados reais. |
| `docs/CORPORATE_ACTIONS.md` | Especificação de eventos corporativos e frações | Norma contábil oficial para a execução da Issue #370. |
| `docs/CORPORATE_EVENT_COMPLEX_ACTIONS_DESIGN.md` | Design técnico de pernas multiativo e persistência | Especificação arquitetural da migration `20261019_corp_event_legs`. |
| `docs/FIXED_INCOME_TAXONOMY_INVENTORY.md` | Inventário de schema e contratos de Renda Fixa | Base técnica da Issue #355. |
| `docs/TOOLS_CALCULATORS.md` | Especificações financeiras das calculadoras | Base técnica da Issue #359. |
| `docs/ARCHITECTURE_DOCTOR.md` | Especificação e catálogo dos 15 invariantes SGI | Catálogo de regras do runner do Architecture Doctor. |

### 7.2 Condições Formais de Invalidação deste Roadmap

Este roadmap deve ser formalmente revisado e atualizado caso qualquer uma das seguintes condições ocorra:
1. **Decisão de Produto em Eventos Corporativos**: Alteração na política de apuração de direitos de bonificação ou leilão de frações que torne obrigatória a nota individual para a exibição de direitos brutos.
2. **Mudança de Política de Provedores**: Modificação na precedência de provedores de mercado (B3 > BRAPI > Yahoo).
3. **Alteração Estrutural de Branching**: Adoção de novo fluxo de integração contínua que altere o papel de `stable-15jun` ou crie branches de release versionadas semanticamente (`v2.x`).
4. **Resolução de Schema em `goals`**: Conclusão da migração de `goals` (#246), momento em que `ALLOWED_DRIFT_TABLES` no Alembic drift gate deverá ser tornado vazio (`set()`).

---

## 8. Verificação Independente e Comandos de Auditoria

Para auditar e verificar independentemente a conformidade do repositório contra as metas deste Roadmap:

```powershell
# 1. Verificar integridade dos checks estáticos do Architecture Doctor (Esperado: exit_code 0)
cd backend
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json

# 2. Verificar conformidade das migrações Alembic e detecção de drift (Após correção de index=True)
cd backend
..\.venv\Scripts\python.exe -m app.governance.alembic_drift_gate

# 3. Executar suíte de testes de contratos determinísticos do backend
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_deterministic_runtime_contract.py -v -p no:cacheprovider

# 4. Executar suíte de testes unitários do frontend via Vitest
cd frontend
npm test -- run src/utils/__tests__/apiError.test.ts

# 5. Consultar saúde e prontidão da stack ativa no Docker Desktop
docker compose ps
docker exec sig-v2-backend-1 curl -s http://localhost:8000/health
docker exec sig-v2-backend-1 curl -s http://localhost:8000/ready
```

---
*Fim do documento `docs/ROADMAP_GOVERNANCE_2026.md` — Aprovado para execução pelo SGI v2 Core Governance.*
