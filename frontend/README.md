# SGI v2 — Frontend (React 19 Core)

Guia técnico, arquitetural e operacional do frontend do **SGI v2 (Sistema de Gestão de Investimentos)**.

> **Documentação Central do Sistema:** Consulte [`docs/DOCUMENTACAO_DO_SISTEMA.md`](../docs/DOCUMENTACAO_DO_SISTEMA.md).
> **Relatório Oficial de Oportunidades de Melhoria:** Consulte [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](../docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md).

---

## 1. Visão Geral da Arquitetura

O frontend do SGI v2 é uma aplicação Single Page Application (SPA) moderna, determinística e altamente responsiva construída com a stack contemporânea:
- **Framework & Runtime:** **React 19** (`^19.3.1`) com **React DOM 19**
- **Tipagem Estrita:** **TypeScript 6** (`^6.0.3`)
- **Build Tool & Bundler:** **Vite 8** (`^8.3.4`)
- **Design System & Estilização:** **Tailwind CSS v4** (`^4.3.3`) com suporte unificado a Dark/Light mode
- **Gerenciamento de Estado de Servidor:** **TanStack Query v5** (`^5.104.4`)
- **Gerenciamento de Estado Global:** **Zustand 5** (`^5.0.15`)
- **Roteamento:** **React Router 7** (`^7.18.4`)
- **Formulários & Schemas:** **React Hook Form 7** (`^7.90.0`) e validação estrita com **Zod 4** (`^4.5.4`)
- **Gráficos e Visualizações:** **Recharts 3** (`^3.10.1`)
- **Ícones:** **Lucide React** (`^1.59.0`)
- **Suíte de Testes:** **Vitest 5** (`^5.0.5`) com Testing Library e JSDOM 29

---

## 2. Estrutura de Diretórios e Componentes

```text
frontend/
├── src/
│   ├── api/                # Clientes Axios tipados e endpoints por domínio
│   ├── components/         # Componentes visuais reutilizáveis
│   │   ├── auth/           # Formulários de login, MFA, aceite de termos (EULA)
│   │   ├── charts/         # Gráficos Recharts (alocação, patrimônio, proventos)
│   │   ├── layout/         # Header, Sidebar, AppLayout e casca de navegação
│   │   ├── portfolio/      # Componentes de carteira, tabelas e AssetDetailDrawer
│   │   ├── proventos/      # Tabela oficial de proventos e calendário de proventos
│   │   └── ui/             # Botões, modais, caixas de diálogo, badges e inputs
│   ├── hooks/              # Custom hooks desacoplados (TanStack Query e UI)
│   ├── pages/              # Páginas e views roteadas da aplicação
│   │   ├── AnalisePage.tsx               # Análise de carteira com IA e diagnóstico de risco
│   │   ├── FixedIncomeCalculatorPage.tsx # Simulador e comparador de títulos de Renda Fixa
│   │   ├── IncomeCalculatorPage.tsx      # Calculadora de aportes e rendimentos futuros
│   │   ├── IrpfPage.tsx                  # Módulo e relatório anual de IRPF
│   │   ├── PatrimonioPage.tsx            # Alocação patrimonial por classes e produtos
│   │   ├── ProventosPage.tsx             # Linha do tempo e tabela oficial de dividendos/JCP
│   │   ├── RentabilidadePage.tsx         # Análise de retorno TWR, MWR e benchmarks
│   │   └── ResumoPage.tsx                # Visão geral da carteira ativa e KPIs rápidos
│   ├── router/             # Definição canônica de rotas e redirecionamentos (/carteira/*)
│   ├── store/              # Stores globais Zustand (sessão, carteira ativa, preferências)
│   └── utils/              # Formatadores de moeda (BRL/USD), datas (date-fns) e percentuais
├── dist/                   # Bundles de produção compilados
├── index.html              # HTML base da SPA
├── package.json            # Dependências oficiais e scripts de automação
├── tsconfig.json           # Configurações do compilador TypeScript
├── vite.config.ts          # Configuração de build e plugins do Vite 8
└── vitest.config.ts        # Configuração do executor de testes Vitest
```

---

## 3. Funcionalidades de Destaque

### 3.1 Motor de Análise e Camada de IA (`AnalisePage.tsx`)
- Implementa a interface corporativa de diagnóstico patrimonial integrando o motor determinístico de análise (#360) e os insights explicativos de Inteligência Artificial (#361).
- Exibe métricas de diversificação, concentração de ativos, risco-retorno versus benchmarks e sínteses executivas em linguagem natural sem delegar cálculos matemáticos à IA.

### 3.2 Gaveta Consolidada de Detalhe do Ativo (`AssetDetailDrawer.tsx`)
- Drawer lateral completo para visualização aprofundada de qualquer ativo sob custódia (#58 / #351).
- Estruturado em abas dinâmicas: Visão Geral, Indicadores Fundamentalistas por classe (adaptados para Ações, FIIs, BDRs, ETFs e Tesouro), Histórico de Cotações com períodos selecionáveis, Proventos Canônicos e Eventos Corporativos.

### 3.3 Simuladores e Calculadoras Financeiras (`IncomeCalculatorPage.tsx` e `FixedIncomeCalculatorPage.tsx`)
- **Calculadora de Rendimentos:** Simulação de aportes periódicos, juros compostos e projeção de renda passiva.
- **Simulador de Renda Fixa:** Comparação lado a lado entre títulos (CDB, LCI, LCA, CRI, CRA, Debêntures e Tesouro) com aplicação automática da tabela regressiva ou isenção fiscal conforme a taxonomia canônica. Operam em memória, sem persistir dados na carteira.

### 3.4 Tabela Oficial de Proventos (`components/proventos/`)
- Apresenta os eventos monetários com detalhamento de tipo (Dividendo, JCP, Rendimento), Data COM (corte), Data de Pagamento e Valor Unitário líquido, consumindo o contrato canônico `pre-prod-dividends-seed.v2` com direitos calculados sob demanda.

### 3.5 Hierarquia Canônica de Roteamento (`/carteira/*`)
- A navegação unificada é centralizada sob a raiz canônica `/carteira/*` (definida em `src/router/portfolioRoutes.ts`).
- Rotas históricas (`/metas`, `/irpf`) possuem redirecionamento automático permanente.
- Acesso condicionado à autenticação prévia com suporte a Google OAuth 2.0 e MFA TOTP (#97).

---

## 4. Comandos de Desenvolvimento e Validação Local

Todas as rotinas do frontend utilizam Node.js 22+ e npm:

### 4.1 Iniciar Servidor de Desenvolvimento Local

```powershell
cd frontend
npm run dev
```

Inicia o servidor Vite na porta `5173` com Hot Module Replacement (HMR).

### 4.2 Verificação Estrita de Tipagem (TypeScript)

```powershell
cd frontend
npm run typecheck
```

Executa `tsc --noEmit` sobre toda a base. O código deve compilar com **zero erros**.

### 4.3 Padronização de Código e Linting (ESLint)

```powershell
cd frontend
npm run lint
```

Executa `eslint . --max-warnings 0`. A base opera com tolerância zero a warnings ou regras desabilitadas.

### 4.4 Execução da Suíte de Testes (Vitest)

```powershell
# Executar toda a suíte de testes unitários e de componentes
cd frontend
npm test -- run

# Executar com relatório de cobertura de código
cd frontend
npm run test:coverage

# Executar em modo interativo de observação
cd frontend
npm run test:watch
```

A suíte possui 65 arquivos de teste e 258 testes automatizados, rodando 100% offline via JSDOM.

### 4.5 Build de Produção

```powershell
cd frontend
npm run build
```

Compila os assets estáticos minificados em `frontend/dist/` e executa o script de validação de bundle.

### 4.6 Auditoria de Dependências de Segurança

```powershell
cd frontend
npx audit-ci
```

---

## 5. Referências e Documentos Correlatos

- [`docs/DOCUMENTACAO_DO_SISTEMA.md`](../docs/DOCUMENTACAO_DO_SISTEMA.md) — Manual unificado do sistema.
- [`docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md`](../docs/DIAGNOSTICO_OPORTUNIDADES_MELHORIA.md) — Diagnóstico detalhado de melhorias.
- [`docs/portfolio-route-hierarchy.md`](../docs/portfolio-route-hierarchy.md) — Especificação detalhada da malha de rotas.
- [`docs/TOOLS_CALCULATORS.md`](../docs/TOOLS_CALCULATORS.md) — Fórmulas e taxonomia fiscal das calculadoras.
