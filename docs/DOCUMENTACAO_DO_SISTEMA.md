# Documentação do Sistema — SGI (Sistema de Gestão de Investimentos)

> **Versão do Sistema:** Produção (Consolidada)  
> **Última Atualização:** 23/10/2026  
> **Status Operacional:** Produtivo (OCI Cloud + Cloudflare Tunnel)  
> **Repositório Central:** `github.com/adrianop/sig-v2`  
> **Branches Oficiais:** `stable-15jun` (desenvolvimento contínuo) | `main` (produção certificada)

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

## 2. Princípios Arquiteturais Obrigatórios

A integridade do SGI é garantida por sete pilares técnicos inegociáveis:

### 2.1 DB-First (Banco de Dados em Primeiro Lugar)
* Os endpoints de leitura financeira (`GET /api/v1/carteira/*`, `/summary`, `/rentabilidade`, `/posicoes`, etc.) **nunca** realizam chamadas a APIs ou provedores externos de mercado.
* Toda a renderização de telas, painéis de controle, relatórios e KPIs é alimentada exclusivamente pelos dados gravados nas tabelas do banco de dados relacional (`assets`, `asset_prices`, `rate_history`, `transactions`, `portfolio_snapshots`).
* Ingestão externa de cotações, proventos e taxas ocorre estritamente por meio de jobs agendados, comandos de sincronização ou bootstrap assíncrono explicitamente autenticado.
* **Proibição de Preços ou Taxas Inventadas:** Se um ativo não possui cotação ou taxa de fechamento registrada para uma data, o sistema expõe explicitamente a pendência em vez de assumir valor zero, paridade 1:1 ou estimativa não fundamentada.

### 2.2 Fonte Canônica Única (`transactions`)
* O livro contábil da aplicação é a tabela `transactions`. Todas as movimentações do ciclo de vida dos investimentos residem nela:
  - `BUY` (Compra / Aplicação)
  - `SELL` (Venda / Resgate)
  - `AMORTIZATION` (Amortização de principal ou rendimento de capital)
  - `DEPOSIT` / `WITHDRAW` (Aporte e retirada financeira da conta corrente)
* Nenhuma projeção paralela deve ser criada para classes específicas (ex: não há tabelas isoladas como `fixed_income_investments` alimentando o patrimônio; toda a posição deriva de `transactions`).

### 2.3 Recálculo Cronológico em Cadeia e Determinismo Temporal
* Quando uma transação no passado é criada, editada ou removida, o sistema recalcula de maneira ordenada todas as posições, custos médios ponderados e resultados subsequentes a partir daquela data efetiva.
* Motores de cálculo sensíveis a datas utilizam serviços de relógio unificados (`Clock` / `FrozenClock`) para garantir que execuções de testes automatizados e reconciliações contábeis sejam 100% reproduzíveis.

### 2.4 Bloqueio Distribuído com Redis (Lease Seguro)
* Rotinas em segundo plano e cron jobs que efetuam escritas massivas de cotações ou consolidação contábil utilizam travas distribuídas no Redis (`lease`) com tempo de expiração (TTL) e token seguro de liberação, prevenindo concorrência mesmo sob réplicas de contêineres.

### 2.5 Isolamento de Contexto e Autorização por Carteira (`PortfolioAccessContext`)
* Todo endpoint que acessa dados de carteira valida se o usuário autenticado é proprietário da carteira solicitada (`portfolio_id`), impedindo acesso horizontal não autorizado.
* Execuções sistêmicas e rotinas agendadas utilizam identificadores explícitos de sistema, sendo vedado o desvio (*bypass*) tácito de segurança.

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

O agendador da aplicação opera via APScheduler no backend FastAPI (`backend/app/core/scheduler.py`). Todas as rotinas operam no fuso horário oficial de Brasília (`America/Sao_Paulo`):

| Horário (BRT) | Nome do Job | Função Técnica | Provedor / Destino |
| :--- | :--- | :--- | :--- |
| **Dias úteis a cada 30m (10h-18h30)** | `intraday_quotes` | Atualiza preços correntes de ações e FIIs em negociação durante o pregão. | BRAPI / Yahoo Finance |
| **Dias úteis às 19:15** | `daily_close_quotes` | Grava o preço oficial de fechamento diário de todos os ativos da B3 em custódia. | BRAPI / Yahoo Finance |
| **Dias úteis às 19:30** | `daily_treasury_rates` | Sincroniza taxas e preços de fechamento de todos os títulos do Tesouro Direto. | Tesouro Transparente (CKAN API) |
| **Dias úteis às 20:40** | `sync_benchmark_rates_daily` | Sincroniza taxas diárias de CDI (série 12), Selic (série 11) e IPCA (série 433) com headers anti-WAF. | Banco Central do Brasil (SGS) |
| **Dias úteis às 20:42** | `sync_ibov_benchmark_daily` | Sincroniza a cotação oficial e calcula o retorno diário do índice IBOVESPA (`^BVSP`). | BRAPI / Yahoo Finance |
| **Dias úteis às 21:00** | `daily_portfolio_snapshots` | Executa a consolidação patrimonial diária gerando os snapshots históricos de todas as carteiras. | Banco de Dados local (`portfolio_snapshots`) |

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
* **Módulo:** `backend/app/integrations/cotahist.py`
* **Uso:** Importação de arquivos anuais padronizados da B3 para carga retroativa auditada e conciliação de preços históricos de pregão.

---

## 6. Frontend e Experiência do Usuário

### 6.1 Stack Tecnológico
* **Core:** React 18, TypeScript 5, Vite 5.
* **Estilização e Design System:** TailwindCSS, Lucide React (ícones), sistema unificado de tokens escuros/claros.
* **Gráficos e Visualizações:** Recharts (evolução patrimonial, alocação de classes, proventos mensais).
* **Formulários e Validação:** React Hook Form e validação de schemas com Zod.
* **Gerenciamento de Estado de Rede:** TanStack Query (React Query) com invalidação de cache e revalidação de dados.

### 6.2 Segurança, Autenticação e Aceite de Termos
* **Fluxo de Autenticação:** JWT com Access Token e Refresh Token seguro. Suporte completo a Segundo Fator de Autenticação (MFA via aplicativo autenticador / TOTP).
* **Modal Compulsório de Termos de Uso e EULA (`RegisterPage.tsx`):**
  - O botão de finalização de cadastro fica estritamente desabilitado até que o usuário abra o modal de Termos de Uso.
  - O modal contém detecção de rolagem ativa (`scroll-to-bottom`): o usuário deve rolar o texto integralmente até a última linha para desbloquear a caixa de seleção de ciência.
  - **Cláusulas Legais Protegidas:** Isenção integral de responsabilidade por perdas patrimoniais decorrentes de decisões do investidor; declaração explícita de que o SGI é uma ferramenta de apoio gerencial e informativo, não prestando consultoria, assessoria ou recomendação de investimentos regulada pela CVM/Anbima; responsabilidade exclusiva do usuário sobre a veracidade dos lançamentos efetuados.

---

## 7. Infraestrutura e Implantação em Produção

### 7.1 Arquitetura de Contêineres (OCI)
A aplicação está implantada na Oracle Cloud Infrastructure (OCI) sob a seguinte composição Docker:

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

### 7.2 Comandos Operacionais no Host OCI
* **Diretório da Aplicação:** `/opt/sgi` (symlink para `/opt/sig-v2`).
* **Verificação de Contêineres:**
  ```bash
  sudo docker ps
  ```
* **Logs da Aplicação:**
  ```bash
  sudo docker logs -f --tail 100 sig-v2-backend-1
  sudo docker logs -f --tail 100 sig-v2-frontend-1
  ```
* **Rebuild e Reinício de Serviços:**
  ```bash
  cd /opt/sgi
  sudo docker compose up -d --build backend frontend
  ```

---

## 8. Governança e Ciclo de Desenvolvimento

* **Branching Model:**
  - `stable-15jun`: Branch principal de desenvolvimento contínuo, integração e homologação.
  - `main`: Branch de código estável e certificado que espelha os deploys de produção.
* **Garantia de Sincronização:** Todas as alterações realizadas no código-fonte devem ser commitadas, testadas com a suíte de testes (Vitest para frontend e Pytest para backend) e imediatamente sincronizadas com o GitHub via `git push origin stable-15jun` e `git push origin main`.
* **Semântica de Migrations:** Toda e qualquer alteração de schema de banco de dados deve ser governada exclusivamente por scripts de migração do Alembic no diretório `backend/alembic/versions/`. Migrações DDL em produção são executadas automaticamente de modo seguro na inicialização do contêiner backend.
