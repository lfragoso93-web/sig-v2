# Documentação do Sistema — SGI (Sistema de Gestão de Investimentos)

> **Versão do Sistema:** Desenvolvimento Contínuo / Pré-Produção
> **Última Atualização:** 29/10/2026
> **Status Operacional:** Ambiente Local Ativo (`docker-compose.yml`, stack `sig-v2`); OCI Cloud em Backlog (#284)
> **Repositório Central:** `github.com/adrianop/sig-v2`
> **Branches Oficiais:** `stable-15jun` (desenvolvimento contínuo obrigatório) | `main` (produção certificada via PR auditada)
> **Relatório Oficial de Oportunidades de Melhoria:** [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md)
> **Subprojetos e Guias de Componentes:** Backend em [`backend/README.md`](../backend/README.md) | Frontend em [`frontend/README.md`](../frontend/README.md)

---

## 1. Visão Geral e Propósito

O **SGI (Sistema de Gestão de Investimentos)** é uma plataforma completa, corporativa e determinística para acompanhamento, consolidação, rentabilidade, apuração tributária (IRPF), controle de proventos e evolução patrimonial de carteiras de investimentos multiclasse.

Diferente de planilhas ou ferramentas de consolidação baseadas em aproximações, o SGI foi desenhado com base em **princípios contábeis estritos**, **arquitetura orientada a dados persistidos (DB-First)** e **motores de recálculo cronológico determinístico**.

### 1.1 Classes de Ativos Suportadas

O sistema unifica e trata de forma especializada as seguintes classes do mercado financeiro brasileiro e internacional:

1. **Renda Variável Brasil (B3):**
   - **Ações:** Ordinárias (ON), Preferenciais (PN), Units.
   - **FIIs:** Fundos de Investimento Imobiliário (tijolo, papel, fundos de fundos, Fiagros).
   - **BDRs:** Brazilian Depositary Receipts negociados na B3.
   - **ETFs Brasil:** Fundos de índice listados na B3 (ex: BOVA11, SMAL11, IVVB11).
2. **Ativos Internacionais:**
   - **Stocks:** Ações negociadas em bolsas dos EUA (NYSE, NASDAQ).
   - **ETFs Globais:** Fundos de índice internacionais (ex: VOO, QQQ, VT).
   - **Câmbio:** Conversão cambial histórica e diária (PTAX / cotações comerciais USD/BRL, EUR/BRL).
3. **Renda Fixa Privada:**
   - **Títulos Bancários e Corporativos:** CDB, LCI, LCA, LC, CRI, CRA e Debêntures (comuns e incentivadas).
   - **Indexadores:** Pós-fixado (% do CDI), Híbrido (IPCA + taxa prefixada) e Prefixado puro (% ao ano).
   - **Taxonomia Fiscal:** Segregação automática de isenção de IRPF (LCI, LCA, CRI, CRA, Debêntures Incentivadas) vs tabela regressiva padrão (CDB, LC, Debêntures comuns).
4. **Títulos Públicos Federais (Tesouro Direto):**
   - Tesouro Selic (LFT), Tesouro IPCA+ (NTN-B Principal), Tesouro IPCA+ com Juros Semestrais (NTN-B), Tesouro Prefixado (LTN/NTN-F), Tesouro RendA+ e Tesouro Educa+.
   - Cotação oficial via integração com API do Tesouro Transparente.
5. **Criptoativos:**
   - Criptomoedas e tokens (ex: Bitcoin, Ethereum) com controle de posições fracionárias e cotações de mercado.

---

## 2. Princípios Arquiteturais e Invariantes

A integridade do SGI é garantida por sete pilares técnicos inegociáveis:

### 2.1 DB-First (Banco de Dados em Primeiro Lugar)
* Os endpoints de leitura financeira (`GET /api/v1/carteira/*`, `/summary`, `/rentabilidade`, `/posicoes`, etc.) **nunca** realizam chamadas a APIs ou provedores externos de mercado.
* Toda a renderização de telas, painéis de controle, relatórios e KPIs é alimentada exclusivamente pelos dados gravados nas tabelas do banco de dados relacional (`assets`, `asset_prices`, `rate_history`, `transactions`, `portfolio_snapshots`).
* Ingestão externa de cotações, proventos e taxas ocorre estritamente por meio de jobs agendados, comandos de sincronização ou bootstrap assíncrono explicitamente autenticado.
* **Proibição de Preços ou Taxas Inventadas:** Se um ativo não possui cotação ou taxa de fechamento registrada para uma data, o sistema expõe explicitamente a pendência em vez de assumir valor zero, paridade 1:1 ou estimativa não fundamentada.

### 2.2 Fonte Canônica Única de Transações (`TransactionWriteService` e `transactions`)
* O livro contábil da aplicação é a tabela `transactions`. Apenas o `TransactionWriteService` possui autoridade para persistir e modificar lançamentos contábeis nessa tabela. Todas as movimentações do ciclo de vida dos investimentos residem nela:
  - `BUY` (Compra / Aplicação)
  - `SELL` (Venda / Resgate)
  - `AMORTIZATION` (Amortização de principal ou rendimento de capital)
  - `DEPOSIT` / `WITHDRAW` (Aporte e retirada financeira da conta corrente)
* Nenhuma projeção paralela deve ser criada para classes específicas (ex: não há tabelas isoladas como `fixed_income_investments` alimentando o patrimônio; toda a posição deriva de `transactions`).

### 2.3 Ponto Único Canônico de Escrita de Snapshots (`PortfolioSnapshotWriterService` — Regra SGI004)
* Apenas o serviço canônico `PortfolioSnapshotWriterService` (`portfolio_snapshot_canonical_twr_service.py`) é autorizado a materializar, atualizar e persistir snapshots patrimoniais nas tabelas `portfolio_snapshots` e `portfolio_class_snapshots`.
* O serviço auxiliar `portfolio_snapshot_service.py` atua exclusivamente no escopo de invalidação sob demanda (`invalidate_snapshots_from`), sendo estritamente vedada qualquer operação de escrita direta (`_upsert_snapshot`, `pg_insert` ou rotinas paralelas de recálculo).
* Esta política de escritor único (*Single Writer Policy*) é fiscalizada ativamente pelo Architecture Doctor sob a regra **`SGI004`** e validada pela suíte `test_portfolio_snapshot_single_writer_policy.py`, garantindo consistência estrita no cálculo da rentabilidade ponderada pelo tempo (TWR) e blindagem contra *race conditions*.

### 2.4 Recálculo Cronológico em Cadeia e Determinismo Temporal (`Clock`)
* Quando uma transação no passado é criada, editada ou removida, o sistema recalcula de maneira ordenada todas as posições, custos médios ponderados e resultados subsequentes a partir daquela data efetiva.
* Motores de cálculo sensíveis a datas utilizam serviços de relógio unificados (`Clock` / `FrozenClock`) para garantir que execuções de testes automatizados e reconciliações contábeis sejam 100% reproduzíveis.

### 2.5 Bloqueio Distribuído com Redis (Lease Seguro)
* Rotinas em segundo plano e cron jobs que efetuam escritas massivas de cotações ou consolidação contábil utilizam travas distribuídas no Redis (`lease`) com tempo de expiração (TTL) e token seguro de liberação, prevenindo concorrência mesmo sob réplicas de contêineres.

### 2.6 Isolamento de Contexto e Autorização por Carteira (`PortfolioAccessContext`)
* Todo endpoint que acessa dados de carteira valida se o usuário autenticado é proprietário da carteira solicitada (`portfolio_id`), impedindo acesso horizontal não autorizado.
* Execuções sistêmicas e rotinas agendadas utilizam identificadores explícitos de sistema (`PortfolioAccessContext.for_system`), sendo vedado o desvio (*bypass*) tácito de segurança.

### 2.7 Tetos de Execução SQL e Proteção N+1 (`assert_max_queries`)
* Leituras financeiras de alta frequência contam com orçamentos explícitos de consultas SQL (`assert_max_queries`), impedindo a introdução de regressões de desempenho do tipo N+1 em consultas relacionais complexas.

---

## 3. Motores de Cálculo e Regras Financeiras

### 3.1 Renda Fixa e Curva de Juros Composta
Para títulos pós-fixados indexados ao CDI, o fator diário acumulado de juros é calculado rigorosamente segundo a convenção de mercado (252 dias úteis):

$$\text{Fator Diário CDI}_d = \left( 1 + \text{CDI Anual}_d \right)^{\frac{1}{252}}$$

$$\text{Taxa Efetiva do Título}_d = 1 + \left( \text{Fator Diário CDI}_d - 1 \right) \times \left( \frac{\text{Percentual do CDI}}{100} \right)$$

O valor atualizado bruto da aplicação em uma data $t$ é dado pelo produto contínuo dos fatores diários a partir da data de aplicação $t_0$:

$$\text{Valor Bruto}_t = \text{Principal} \times \prod_{d=t_0 + 1}^{t} \text{Taxa Efetiva do Título}_d$$

* **Fail-Safe Rate Compounding:** Se houver feriado bancário, aplica-se a convenção de dias úteis (ANBIMA). Se faltar a taxa diária de um dia útil no banco de dados, o motor interrompe a capitalização no último dia confiável e sinaliza a necessidade de sincronização, garantindo que valores irreais não sejam projetados.

### 3.2 Renda Variável: Custo Médio e Resultado Realizado
* **Custo Médio Ponderado:** Cada nova compra ajusta o preço médio contábil considerando a quantidade e o preço unitário acrescido das taxas de corretagem e emolumentos:
  $$\text{Novo PM} = \frac{(\text{Qtd Anterior} \times \text{PM Anterior}) + (\text{Qtd Comprada} \times \text{Preço Aquisição}) + \text{Taxas}}{\text{Qtd Anterior} + \text{Qtd Comprada}}$$
* **Realização de Venda:** A venda reduz a quantidade em custódia sem alterar o preço médio das cotas remanescentes. O lucro ou prejuízo é calculado subtraindo o custo médio ponderado e os custos operacionais do valor total da venda:
  $$\text{Resultado} = \text{Valor Bruto Venda} - \text{Taxas} - (\text{Qtd Vendida} \times \text{PM})$$

### 3.3 Proventos e Direitos (Dividendos e JCP)
* **Persistência Centralizada:** Os eventos de proventos dos ativos são gravados em `asset_dividends` com: Data-Com (*cut-off date*), Data de Pagamento, Tipo de Provento (Dividendo, JCP, Rendimento FII) e Valor por Cota.
* **Projeção Sob Demanda:** Os direitos de cada carteira são calculados multiplicando o valor unitário pela quantidade de cotas que a carteira possuía na data-com do evento.
* **Retenção Fiscal:**
  - **Dividendos / Rendimentos FII:** Isentos de IR para pessoa física (conforme legislação vigente).
  - **JCP (Juros sobre Capital Próprio):** Retenção automática de 15% de IRPF na fonte.

### 3.4 Eventos Corporativos
* A tabela `corporate_events` registra desdobramentos (*splits*), grupamentos (*reverse splits*) e bonificações.
* As transações originais nunca são modificadas. A posição histórica e o preço médio são ajustados proporcionalmente pelo fator do evento corporativo a partir da sua data de vigência.

### 3.5 Rentabilidade (TWR / MWR) e Benchmarks
* **TWR (Time-Weighted Rate of Return):** Elimina distorções causadas por novos aportes e resgates volumosos, permitindo comparação justa com os índices de mercado.
* **Benchmarks Nativos:**
  - **CDI:** Taxa diária anualizada (série SGS 12).
  - **Selic:** Taxa diária anualizada (série SGS 11).
  - **IPCA:** Variação mensal oficial (série SGS 433) com interpolação diária.
  - **IBOVESPA:** Variação percentual diária do índice oficial da B3 (`^BVSP`).
  - **IFIX:** Índice de Fundos Imobiliários.

### 3.6 Motor Fiscal e IRPF
* **Renda Variável Geral:** Isenção de imposto sobre ganho de capital para alienações de Ações até R$ 20.000,00 no mês calendário (operações normais/swing trade). Day trade e FIIs são tributados sem isenção de volume (20%).
* **Compensação de Prejuízos:** Prejuízos apurados em meses anteriores na mesma modalidade são compensados automaticamente com lucros futuros antes do cálculo do imposto devido.
* **Tabela Regressiva de Renda Fixa:** Aplicação automática das alíquotas com base no prazo decorrido entre a aplicação e a data de apuração ou resgate (22,5%, 20%, 17,5% ou 15%).

---

## 4. Automação em Segundo Plano (Scheduler)

O agendador da aplicação opera via APScheduler no backend FastAPI (`backend/app/core/scheduler.py`). Todas as rotinas operam no fuso horário oficial de Brasília (`America/Sao_Paulo`) e utilizam bloqueio distribuído no Redis via `distributed_job_lock` com comportamento *fail-closed*, prevenindo conflitos concorrentes entre múltiplas instâncias ou workers:

| Horário (BRT) | ID do Job | Função Técnica | Provedor / Destino | Bloqueio / Lock |
| :--- | :--- | :--- | :--- | :--- |
| **Dias úteis a cada 90m (09h-18h)** | `update_quotes_intraday_full_hour`<br>`update_quotes_intraday_half_hour` | Atualiza preços correntes de ativos negociados (Ações, FIIs, BDRs, ETFs, Stocks, Cripto, Tesouro) durante o pregão (09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00). | Provedores de mercado / Banco local (`asset_prices`) | Redis Lock (TTL 7200s) |
| **Dias úteis às 08:30** | `notify_daily_dividend_payments` | Envia notificação matinal por e-mail contendo o resumo dos proventos que têm pagamento previsto para o dia. | Notificação transacional / E-mail | Redis Lock (TTL 3600s) |
| **Dias úteis às 20:40** | `sync_benchmark_rates_daily` | Sincroniza taxas diárias de CDI (série 12), Selic (série 11) e IPCA (série 433) com headers anti-WAF (sob flag `ENABLE_DAILY_BENCHMARK_SYNC`). | Banco Central do Brasil (SGS) / `rate_history` | Redis Lock (TTL 3600s) |
| **Dias úteis às 20:42** | `sync_ibov_benchmark_daily` | Sincroniza a cotação oficial e calcula o retorno diário do índice IBOVESPA (`^BVSP`) (sob flag `ENABLE_DAILY_BENCHMARK_SYNC`). | Provedor de cotações / `asset_prices` | Redis Lock (TTL 3600s) |
| **Dias úteis às 20:45** | `persist_daily_close_prices` | Grava o preço oficial de fechamento diário de todos os ativos da B3 e internacionais sob custódia. | Provedor de cotações / `asset_prices` | Redis Lock (TTL 7200s) |
| **Dias úteis às 20:50** | `persist_treasury_daily_close` | Sincroniza taxas e preços de fechamento de todos os títulos do Tesouro Direto. | Tesouro Transparente (CKAN API) / `asset_prices` | Redis Lock (TTL 7200s) |
| **Dias úteis às 21:00** | `portfolio_snapshot_auto_maintenance` | Executa a consolidação patrimonial diária gerando os snapshots históricos e calculando a rentabilidade TWR de todas as carteiras. | Banco de Dados local (`portfolio_snapshots`) | Redis Lock (TTL 7200s) |
| **Dias úteis às 21:30** | `refresh_asset_fundamentals_daily` | Atualiza indicadores fundamentalistas, métricas financeiras e consenso de analistas para os ativos em custódia e catálogo. | Provedores fundamentalistas / Banco local | Redis Lock (TTL 7200s) |
| **Dia 01 do mês às 08:15** | `audit_b3_market_calendar_monthly` | Realiza auditoria read-only da fonte oficial do calendário de negociação da B3 para detectar divergências de feriados e dias úteis (sob flag `ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT`). | Calendário Oficial B3 / Log e relatório de auditoria | Redis Lock (TTL 300s) |

---

## 5. Provedores de Dados e Integrações

### 5.1 Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (BCB SGS)
* **Módulo:** `backend/app/integrations/bcb_sgs.py`
* **Séries Monitoradas:**
  - `12`: CDI diário (em % ao dia).
  - `11`: Selic diária (em % ao dia).
  - `433`: IPCA mensal (em % ao mês).
* **Resiliência:** Requisições formatadas com cabeçalhos HTTP de navegador (`User-Agent`, `Accept: application/json`), validação de conteúdo JSON para evitar interceptações de páginas HTML de bloqueio e retries com backoff exponencial.

### 5.2 Tesouro Transparente
* **Módulo:** `backend/app/integrations/tesouro_transparente.py`
* **Fonte:** Repositório oficial de dados abertos do Tesouro Nacional.
* **Mapeamento:** Preço unitário base, taxa de compra e taxa de venda diária para todos os títulos públicos federais.

### 5.3 BRAPI e Yahoo Finance
* **Módulos:** `backend/app/integrations/brapi.py` e `backend/app/integrations/yfinance_client.py`
* **Uso:** Cotações históricas diárias, dividendos declarados e cotações correntes.

### 5.4 B3 COTA HIST
* **Módulo:** `backend/app/integrations/b3_cotahist.py`
* **Uso:** Importação de arquivos anuais padronizados da B3 para carga retroativa auditada e conciliação de preços históricos de pregão.

---

## 6. Frontend e Experiência do Usuário

### 6.1 Stack Tecnológico
* **Core:** React 19 (`^19.3.1`), TypeScript 6 (`^6.0.3`), Vite 8 (`^8.3.4`).
* **Estilização e Design System:** Tailwind CSS v4 (`^4.3.3`), Lucide React (`^1.59.0`), sistema unificado de tokens escuros/claros.
* **Gráficos e Visualizações:** Recharts 3 (`^3.10.1`) (evolução patrimonial, alocação de classes, proventos mensais).
* **Formulários e Validação:** React Hook Form 7 (`^7.90.0`) e validação de schemas com Zod 4 (`^4.5.4`).
* **Gerenciamento de Estado de Rede:** TanStack Query v5 (`^5.104.4`) com invalidação de cache e revalidação de dados.
* **Gerenciamento de Estado Global:** Zustand 5 (`^5.0.15`).
* **Roteamento:** React Router 7 (`^7.18.4`) sob a hierarquia canônica `/carteira/*`.
* **Suíte de Testes:** Vitest 5 (`^5.0.5`) com Testing Library e JSDOM 29.
* **Guia Dedicado do Frontend:** [`frontend/README.md`](../frontend/README.md).

### 6.2 Segurança, Autenticação e Aceite de Termos
* **Fluxo de Autenticação:** JWT com Access Token e Refresh Token seguro. Suporte completo a Segundo Fator de Autenticação (MFA via aplicativo autenticador / TOTP).
* **Modal Compulsório de Termos de Uso e EULA (`RegisterPage.tsx`):**
  - O botão de finalização de cadastro fica estritamente desabilitado até que o usuário abra o modal de Termos de Uso.
  - O modal contém detecção de rolagem ativa (`scroll-to-bottom`): o usuário deve rolar o texto integralmente até a última linha para desbloquear a caixa de seleção de ciência.
  - **Cláusulas Legais Protegidas:** Isenção integral de responsabilidade por perdas patrimoniais decorrentes de decisões do investidor; declaração explícita de que o SGI é uma ferramenta de apoio gerencial e informativo, não prestando consultoria, assessoria ou recomendação de investimentos regulada pela CVM/Anbima; responsabilidade exclusiva do usuário sobre a veracidade dos lançamentos efetuados.

---

## 7. Infraestrutura e Implantação

### 7.1 Runtime de Desenvolvimento e Validação Local (`docker-compose.yml`)
O ambiente primário e oficial de desenvolvimento, testes e validação é a composição Docker local (`docker-compose.yml`, stack `sig-v2`):
- Composição: `frontend` (porta 5173/80), `backend` (FastAPI na porta 8000), `db` (PostgreSQL 16 na porta 5432) e `redis` (Redis 7 na porta 6379).
- Toda validação com usuários e testes assistidos é conduzida nesta stack única (`sig-v2`). Stacks isoladas anteriores (como `sgi-usertest`) foram descontinuadas.

### 7.2 Arquitetura de Nuvem (OCI — Backlog #284)
A topologia de nuvem em Oracle Cloud Infrastructure (OCI) e Cloudflare Tunnel está documentada como alvo de infraestrutura e backlog (#284):

```text
                                Cloudflare Network
                                       │ (Tunnel Seguro TLS)
                                       ▼
                             ┌───────────────────┐
                             │    cloudflared    │
                             └─────────┬─────────┘
                                       │ (Porta 80 interna)
                                       ▼
                             ┌───────────────────┐
                             │     frontend      │ (Nginx Alpine)
                             └─────────┬─────────┘
                                       │ /api/v1/ (Proxy reverso)
                                       ▼
                             ┌───────────────────┐
                             │      backend      │ (FastAPI + Uvicorn)
                             └────┬─────────┬────┘
                                  │         │
                 ┌────────────────┘         └────────────────┐
                 ▼                                           ▼
       ┌───────────────────┐                       ┌───────────────────┐
       │     Postgres      │ (Porta 5432)          │       Redis       │ (Porta 6379)
       │    (pgvector)     │                       │     (Leases)      │
       └───────────────────┘                       └───────────────────┘
```

1. **`sig-v2-frontend-1`**: Contêiner Nginx rodando em Alpine Linux sem privilégios de root (`nginx`), servindo os arquivos estáticos compilados do React e atuando como proxy reverso para as chamadas `/api/v1/*`.
2. **`sig-v2-backend-1`**: Contêiner Python 3.12 Slim executando sob o usuário `app`. Inicializa executando migrations Alembic de forma transacional e segura no `entrypoint.sh` antes de subir o servidor Uvicorn.
3. **`sig-v2-db-1`**: Banco de dados PostgreSQL 16 com volume Docker persistente.
4. **`sig-v2-redis-1`**: Servidor Redis 7 com verificação periódica de saúde (`redis-cli ping`).
5. **`sig-v2-cloudflared-1`**: Conector oficial Cloudflare Tunnel que conecta a instância à nuvem sem necessidade de abrir portas públicas ou alocar IP público de entrada.

---

## 8. Governança e Ciclo de Desenvolvimento

* **Branching Model e Fluxo de PR:**
  - `stable-15jun`: Branch principal e mandatória de desenvolvimento contínuo, integração e homologação. Todas as alterações, branches de trabalho e commits locais devem ter como base e destino `stable-15jun`.
  - `main`: Branch de código estável e certificado que espelha os deploys de produção. `main` recebe exclusivamente macroblocos promovidos via Pull Request formal e auditada. **É terminantemente vedado efetuar `git push` direto para `main`**.
* **Garantia de Qualidade Pré-Commit:** Todas as alterações realizadas no código-fonte devem ser commitadas em `stable-15jun`, testadas com as suítes locais completas (Vitest para frontend, Pytest, Mypy, Flake8 e Architecture Doctor para backend) e sincronizadas com o repositório remoto via `git push origin stable-15jun`.
* **Semântica de Migrations:** Toda e qualquer alteração de schema de banco de dados deve ser governada exclusivamente por scripts de migração do Alembic no diretório `backend/alembic/versions/`. Migrações DDL em produção são executadas automaticamente de modo seguro na inicialização do contêiner backend (`entrypoint.sh`). A cabeça linear ativa é `20261022_auth_oauth_mfa`.
