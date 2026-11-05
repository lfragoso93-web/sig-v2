import { Link } from 'react-router-dom'
import {
  TrendingUp,
  Wallet,
  ShieldCheck,
  BarChart2,
  ArrowRight,
  ChevronRight,
  Layers,
  FileText,
  Sparkles,
  Lock,
  Clock,
  CheckCircle2,
  DollarSign,
  Globe2,
  HelpCircle,
  PieChart,
} from 'lucide-react'
import LogoSGI from '@/components/ui/LogoSGI'

// ── Classes de Ativos Suportadas ─────────────────────────────────────────────────────────────
const ASSET_CLASSES = [
  {
    name: 'Ações Brasileiras',
    type: 'B3',
    examples: 'PETR4, VALE3, WEGE3, ITUB4',
    badge: 'Isenção R$ 20k/mês',
    color: 'var(--color-primary)',
    desc: 'Cálculo automático de preço médio ponderado, ganho líquido e controle de proventos com data com/ex.',
  },
  {
    name: 'Fundos Imobiliários',
    type: 'FIIs & FI-Infra',
    examples: 'HGLG11, MXRF11, XPML11, KNIP11',
    badge: 'Rendimentos Isentos',
    color: 'var(--color-gold)',
    desc: 'Acompanhamento do yield on cost, dividendos mensais creditados e separação fiscal automática de alienações.',
  },
  {
    name: 'Renda Fixa & Crédito',
    type: 'Privada',
    examples: 'CDB, LCI, LCA, CRI, CRA, Debêntures',
    badge: 'Tabela Regressiva',
    color: 'var(--color-blue)',
    desc: 'Gestão de prazos de carência, liquidez diária, indexadores (CDI/IPCA/Prefixado) e apuração do IR na fonte.',
  },
  {
    name: 'Tesouro Direto',
    type: 'Soberano',
    examples: 'Selic, IPCA+, Prefixado, RendA+',
    badge: 'Garantia Tesouro Nacional',
    color: 'var(--color-success)',
    desc: 'Cálculo de marcação a mercado diária, PU oficial da STN e acompanhamento do vencimento de títulos públicos.',
  },
  {
    name: 'Ativos Globais & Stocks',
    type: 'Internacional',
    examples: 'AAPL, MSFT, NVDA, SPY, QQQ',
    badge: 'Cotação em USD + PTAX',
    color: 'var(--color-purple)',
    desc: 'Gestão em moeda estrangeira com conversão cambial automatizada e cálculo de ganho de capital em moeda forte.',
  },
  {
    name: 'Criptomoedas',
    type: 'Ativos Digitais',
    examples: 'Bitcoin (BTC), Ethereum (ETH), Solana',
    badge: 'Precisão 8 decimais',
    color: 'var(--color-orange)',
    desc: 'Suporte a frações de alta precisão, custódia descentralizada e cotação em tempo real com paridade cambial.',
  },
  {
    name: 'BDRs & Recibos',
    type: 'B3 Internacional',
    examples: 'AMZO34, GOGL34, MELI34',
    badge: 'Liquidação em Reais',
    color: 'var(--color-primary)',
    desc: 'Invista nas maiores companhias globais diretamente pela bolsa brasileira com proventos em reais.',
  },
  {
    name: 'ETFs Nacionais',
    type: 'Fundos de Índice',
    examples: 'BOVA11, SMAL11, IVVB11',
    badge: 'Diversificação Ampla',
    color: 'var(--color-blue)',
    desc: 'Exposição a índices de mercado brasileiros e globais com cálculo de tributação de 15% nas vendas com lucro.',
  },
]

// ── Pilares Tecnológicos & Financeiros ───────────────────────────────────────────────────────
const PILLARS = [
  {
    icon: TrendingUp,
    title: 'Rentabilidade Real por TWR e MWR',
    desc: 'Elimina totalmente as distorções causadas por novos aportes ou retiradas financeiras. O SGI adota o método Time-Weighted Return (TWR) — padrão da indústria de fundos — permitindo comparar sua performance real contra CDI, IPCA e IBOVESPA.',
    highlight: 'Comparativo oficial vs. Benchmarks',
  },
  {
    icon: Layers,
    title: 'Custódia Consolidada Multiclasse',
    desc: 'Acabe de vez com planilhas paralelas e extratos fragmentados. Gerencie simultaneamente renda variável nacional, fundos imobiliários, títulos públicos, crédito privado, moedas estrangeiras e criptoativos em uma visão consolidada.',
    highlight: '8 classes integradas em um só painel',
  },
  {
    icon: FileText,
    title: 'Radar Fiscal & Conformidade IRPF',
    desc: 'Automatize a rotina tributária dos seus investimentos. Apuração de ganhos líquidos com retenção na fonte (dedo-duro), faixa de isenção de R$ 20.000 em ações, controle acumulado de prejuízos compensáveis e extratos prontos para a DIRPF anual.',
    highlight: 'Declaração anual sem dores de cabeça',
  },
  {
    icon: Sparkles,
    title: 'Assistente IA & Gestão por Metas',
    desc: 'Assistente cognitivo fundamentado estritamente na documentação canônica do sistema, orientando sua navegação. Motor inteligente de rebalanceamento que calcula exatamente onde aportar para atingir suas metas estratégicas.',
    highlight: 'Decisões guiadas por dados',
  },
]

// ── Perguntas Frequentes ─────────────────────────────────────────────────────────────────────
const FAQS = [
  {
    q: 'O que diferencia o SGI de outras plataformas e planilhas?',
    a: 'O SGI foi construído com arquitetura financeira institucional: rentabilidade calculada pelo TWR puro (Time-Weighted Return), fechamento diário automatizado com persistência às 21h, controle fiscal com compensação de prejuízos e conformidade com a regulamentação brasileira (B3 e Receita Federal).',
  },
  {
    q: 'O SGI é gratuito?',
    a: 'Sim. A plataforma é uma ferramenta de gestão patrimonial pessoal desenvolvida para oferecer controle irrestrito ao investidor, sem planos ocultos nem cobranças por quantidade de carteiras cadastradas.',
  },
  {
    q: 'Como o SGI trata a segurança e a privacidade dos meus dados?',
    a: 'Sua segurança é prioridade absoluta. O SGI oferece autenticação em dois fatores (2FA / MFA via TOTP), isolamento lógico individualizado de contas, senhas com hashing de alta resistência e zero compartilhamento de saldos ou dados financeiros com modelos de IA públicos.',
  },
  {
    q: 'Posso cadastrar mais de uma carteira de investimentos?',
    a: 'Sim. Você pode criar carteiras independentes para cada objetivo ou corretora (por exemplo: "Previdência", "Dividendos", "Investimentos Globais") e alternar entre elas instantaneamente com um clique na barra superior.',
  },
]

export default function Landing() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--color-bg)',
        color: 'var(--color-text)',
        overflowX: 'hidden',
        position: 'relative',
      }}
    >
      {/* ── Background Glow Decorativo ── */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 'min(1200px, 100vw)',
          height: '650px',
          background:
            'radial-gradient(ellipse 65% 55% at 50% 0%, oklch(from var(--color-primary) l c h / 0.14), transparent 75%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* ── Navbar ── */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.875rem clamp(1rem, 4vw, 3.5rem)',
          borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          background: 'oklch(from var(--color-bg) l c h / 0.88)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
            <LogoSGI size={30} />
          </Link>

          <nav
            className="hidden md:flex"
            style={{ alignItems: 'center', gap: '1.5rem', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}
          >
            <a href="#recursos" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 150ms' }}>
              Recursos
            </a>
            <a href="#ativos" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 150ms' }}>
              Classes de Ativos
            </a>
            <a href="#twr" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 150ms' }}>
              Metodologia TWR
            </a>
            <a href="#seguranca" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 150ms' }}>
              Segurança
            </a>
            <a href="#faq" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 150ms' }}>
              FAQ
            </a>
          </nav>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link
            to="/auth/login"
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 500,
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-lg)',
              color: 'var(--color-text)',
              textDecoration: 'none',
              transition: 'background 150ms ease',
            }}
          >
            Entrar
          </Link>
          <Link
            to="/auth/registro"
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              padding: '0.5rem 1.25rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.375rem',
              boxShadow: '0 4px 14px oklch(from var(--color-primary) l c h / 0.28)',
              transition: 'transform 150ms ease, box-shadow 150ms ease',
            }}
          >
            Começar grátis
            <ArrowRight size={15} />
          </Link>
        </div>
      </header>

      <main style={{ flex: 1, position: 'relative', zIndex: 1 }}>
        {/* ── Hero Principal ── */}
        <section
          style={{
            padding: '4.5rem clamp(1rem, 4vw, 3rem) 3.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            maxWidth: '1200px',
            margin: '0 auto',
          }}
        >
          {/* Badge institucional — Sem menção de versão */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.625rem',
              padding: '0.45rem 1rem',
              borderRadius: '9999px',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              letterSpacing: '0.01em',
              marginBottom: '1.75rem',
              border: '1px solid oklch(from var(--color-primary) l c h / 0.25)',
              background: 'oklch(from var(--color-primary) l c h / 0.08)',
              color: 'var(--color-primary)',
              boxShadow: '0 2px 8px oklch(from var(--color-primary) l c h / 0.1)',
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '9999px',
                background: 'var(--color-primary)',
                boxShadow: '0 0 8px var(--color-primary)',
              }}
            />
            Plataforma de Gestão Patrimonial e Inteligência de Carteiras
          </div>

          <h1
            style={{
              fontSize: 'clamp(2.25rem, 5.5vw, 3.85rem)',
              fontWeight: 800,
              lineHeight: 1.15,
              maxWidth: '52rem',
              marginBottom: '1.5rem',
              letterSpacing: '-0.035em',
              color: 'var(--color-text)',
            }}
          >
            Controle patrimonial definitivo com{' '}
            <span
              style={{
                background: 'linear-gradient(135deg, var(--color-primary), oklch(from var(--color-primary) l c 160))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              precisão institucional
            </span>
          </h1>

          <p
            style={{
              fontSize: 'clamp(1rem, 2vw, 1.1875rem)',
              maxWidth: '44rem',
              marginBottom: '2.5rem',
              lineHeight: 1.65,
              color: 'var(--color-text-muted)',
            }}
          >
            Consolidação multiclasse sem fronteiras. Acompanhe rentabilidade real pelo{' '}
            <strong style={{ color: 'var(--color-text)', fontWeight: 600 }}>TWR puro</strong>, proventos futuros, fechamento diário
            automatizado e conformidade IRPF para B3, Renda Fixa, Cripto e Ativos Globais.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.875rem', justifyContent: 'center', marginBottom: '2.5rem' }}>
            <Link
              to="/auth/registro"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.625rem',
                padding: '0.875rem 2rem',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--color-primary)',
                color: 'var(--color-text-inverse)',
                fontSize: 'var(--text-base)',
                fontWeight: 650,
                textDecoration: 'none',
                boxShadow: '0 6px 20px oklch(from var(--color-primary) l c h / 0.35)',
                transition: 'transform 150ms ease, box-shadow 150ms ease',
              }}
            >
              Criar conta gratuita
              <ArrowRight size={18} />
            </Link>

            <Link
              to="/auth/login"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.875rem 1.75rem',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                fontSize: 'var(--text-base)',
                fontWeight: 600,
                textDecoration: 'none',
                transition: 'background 150ms ease, border-color 150ms ease',
              }}
            >
              Acessar plataforma
              <ChevronRight size={18} />
            </Link>
          </div>

          {/* Badges de confiança institucionais */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '1.25rem 2rem',
              fontSize: 'var(--text-xs)',
              fontWeight: 500,
              color: 'var(--color-text-muted)',
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
              <CheckCircle2 size={15} color="var(--color-success)" /> Cálculo TWR & MWR Auditado
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
              <CheckCircle2 size={15} color="var(--color-success)" /> 8 Classes em Custódia Unificada
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
              <CheckCircle2 size={15} color="var(--color-success)" /> Fechamento Oficial Diário às 21h
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
              <CheckCircle2 size={15} color="var(--color-success)" /> Autenticação Segura com 2FA (TOTP)
            </span>
          </div>
        </section>

        {/* ── Mockup Executivo Imponente da Plataforma ── */}
        <section
          id="recursos"
          style={{
            padding: '0 clamp(1rem, 4vw, 3rem) 5.5rem',
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '68rem',
              borderRadius: 'var(--radius-2xl)',
              overflow: 'hidden',
              border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
              background: 'var(--color-surface)',
              boxShadow: '0 24px 60px oklch(0 0 0 / 0.35), 0 0 0 1px oklch(from var(--color-primary) l c h / 0.08)',
            }}
          >
            {/* Barra de controle da janela */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1.25rem',
                borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                background: 'var(--color-surface-offset)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ width: 11, height: 11, borderRadius: '9999px', background: '#ff5f57' }} />
                <span style={{ width: 11, height: 11, borderRadius: '9999px', background: '#febc2e' }} />
                <span style={{ width: 11, height: 11, borderRadius: '9999px', background: '#28c840' }} />
                <span
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    marginLeft: '0.75rem',
                    color: 'var(--color-text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <LogoSGI size={18} iconOnly />
                  SGI — Carteira Principal • Snapshot Oficial em Tempo Real
                </span>
              </div>
              <div
                style={{
                  fontSize: 'var(--text-2xs, 0.6875rem)',
                  fontWeight: 600,
                  color: 'var(--color-success)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  background: 'oklch(from var(--color-success) l c h / 0.12)',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '9999px',
                }}
              >
                <Clock size={12} />
                Snapshot 21h Sincronizado
              </div>
            </div>

            {/* Painel Interno do Mockup */}
            <div style={{ padding: 'clamp(1rem, 2.5vw, 1.75rem)' }}>
              {/* Grid de KPIs Executivos */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '0.875rem',
                  marginBottom: '1.5rem',
                }}
              >
                <div
                  style={{
                    background: 'var(--color-surface-offset)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.125rem',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                  }}
                >
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    Patrimônio Consolidado
                  </span>
                  <div
                    style={{
                      fontSize: 'var(--text-xl)',
                      fontWeight: 750,
                      color: 'var(--color-text)',
                      marginTop: '0.25rem',
                    }}
                  >
                    R$ 342.850,00
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-success)',
                      fontWeight: 600,
                      marginTop: '0.25rem',
                    }}
                  >
                    +R$ 41.220,00 (+13,7%) no ano
                  </div>
                </div>

                <div
                  style={{
                    background: 'var(--color-surface-offset)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.125rem',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                  }}
                >
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    Rentabilidade Real (TWR)
                  </span>
                  <div
                    style={{
                      fontSize: 'var(--text-xl)',
                      fontWeight: 750,
                      color: 'var(--color-primary)',
                      marginTop: '0.25rem',
                    }}
                  >
                    +19,85%
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-success)',
                      fontWeight: 600,
                      marginTop: '0.25rem',
                    }}
                  >
                    Alpha de +8,60% vs. CDI (11,25%)
                  </div>
                </div>

                <div
                  style={{
                    background: 'var(--color-surface-offset)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.125rem',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                  }}
                >
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    Proventos Acumulados
                  </span>
                  <div
                    style={{
                      fontSize: 'var(--text-xl)',
                      fontWeight: 750,
                      color: 'var(--color-gold)',
                      marginTop: '0.25rem',
                    }}
                  >
                    R$ 16.480,00
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-text-muted)',
                      fontWeight: 500,
                      marginTop: '0.25rem',
                    }}
                  >
                    Yield on Cost médio de 9,6% a.a.
                  </div>
                </div>

                <div
                  style={{
                    background: 'var(--color-surface-offset)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.125rem',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                  }}
                >
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    Fechamento Fiscal (Mês)
                  </span>
                  <div
                    style={{
                      fontSize: 'var(--text-xl)',
                      fontWeight: 750,
                      color: 'var(--color-text)',
                      marginTop: '0.25rem',
                    }}
                  >
                    R$ 0,00 a pagar
                  </div>
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-success)',
                      fontWeight: 600,
                      marginTop: '0.25rem',
                    }}
                  >
                    Isenção R$ 20k • Prejuízo: R$ 4.250
                  </div>
                </div>
              </div>

              {/* Tabela de Posições Reais Representativas */}
              <div
                style={{
                  borderRadius: 'var(--radius-xl)',
                  border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                  overflowX: 'auto',
                  background: 'var(--color-surface-offset)',
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)', color: 'var(--color-text-muted)' }}>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Ativo</th>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Classe</th>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600, textAlign: 'right' }}>Qtd</th>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600, textAlign: 'right' }}>Preço Médio</th>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600, textAlign: 'right' }}>Cotação Atual</th>
                      <th style={{ padding: '0.75rem 1rem', fontWeight: 600, textAlign: 'right' }}>Rentabilidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { ticker: 'PETR4', name: 'Petrobras PN', class: 'Ações B3', qty: '400', pm: 'R$ 31,80', cur: 'R$ 38,40', gain: '+20,7%', pos: true },
                      { ticker: 'MXRF11', name: 'Maxi Renda FII', class: 'FIIs', qty: '1.200', pm: 'R$ 10,08', cur: 'R$ 10,85', gain: '+7,6%', pos: true },
                      { ticker: 'IPCA+ 2035', name: 'Tesouro IPCA+', class: 'Tesouro Direto', qty: '18,5', pm: 'R$ 3.120,00', cur: 'R$ 3.480,00', gain: '+11,5%', pos: true },
                      { ticker: 'AAPL', name: 'Apple Inc.', class: 'Stocks (USD)', qty: '25', pm: 'US$ 184,00', cur: 'US$ 232,50', gain: '+26,3%', pos: true },
                      { ticker: 'BTC', name: 'Bitcoin', class: 'Criptoativo', qty: '0,185', pm: 'US$ 64.200', cur: 'US$ 96.400', gain: '+50,1%', pos: true },
                    ].map((row) => (
                      <tr
                        key={row.ticker}
                        style={{
                          borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                        }}
                      >
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 650, color: 'var(--color-text)' }}>
                          <div>{row.ticker}</div>
                          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontWeight: 400 }}>{row.name}</div>
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: 'var(--color-text-muted)' }}>
                          <span
                            style={{
                              fontSize: 'var(--text-xs)',
                              padding: '0.2rem 0.5rem',
                              borderRadius: 'var(--radius-md)',
                              background: 'oklch(from var(--color-primary) l c h / 0.08)',
                              color: 'var(--color-primary)',
                              fontWeight: 500,
                            }}
                          >
                            {row.class}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{row.qty}</td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-muted)' }}>
                          {row.pm}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                          {row.cur}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem 1rem',
                            textAlign: 'right',
                            fontVariantNumeric: 'tabular-nums',
                            fontWeight: 650,
                            color: row.pos ? 'var(--color-success)' : 'var(--color-notification)',
                          }}
                        >
                          {row.gain}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* ── Seção de Pilares Arquiteturais (4 Forças do SGI) ── */}
        <section
          id="twr"
          style={{
            padding: '5rem clamp(1rem, 4vw, 3.5rem)',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
            background: 'oklch(from var(--color-surface) l c h / 0.4)',
          }}
        >
          <div style={{ maxWidth: '68rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
              <h2
                style={{
                  fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                  fontWeight: 800,
                  letterSpacing: '-0.025em',
                  marginBottom: '0.875rem',
                  color: 'var(--color-text)',
                }}
              >
                Engenharia financeira e rigor matemático
              </h2>
              <p style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-muted)', maxWidth: '38rem', margin: '0 auto' }}>
                Construído para investidores que exigem veracidade nos números e autonomia sobre seus dados.
              </p>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1.25rem',
              }}
            >
              {PILLARS.map((p) => {
                const Icon = p.icon
                return (
                  <div
                    key={p.title}
                    style={{
                      background: 'var(--color-surface)',
                      border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                      borderRadius: 'var(--radius-xl)',
                      padding: '1.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.875rem',
                      transition: 'transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease',
                    }}
                  >
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 'var(--radius-lg)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'oklch(from var(--color-primary) l c h / 0.1)',
                        color: 'var(--color-primary)',
                      }}
                    >
                      <Icon size={22} />
                    </div>

                    <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-text)' }}>{p.title}</h3>

                    <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.65, color: 'var(--color-text-muted)', flex: 1 }}>{p.desc}</p>

                    <div
                      style={{
                        fontSize: 'var(--text-xs)',
                        fontWeight: 600,
                        color: 'var(--color-primary)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.375rem',
                        marginTop: '0.5rem',
                      }}
                    >
                      <CheckCircle2 size={13} />
                      {p.highlight}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* ── Classes de Ativos Suportadas ── */}
        <section
          id="ativos"
          style={{
            padding: '5rem clamp(1rem, 4vw, 3.5rem)',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          }}
        >
          <div style={{ maxWidth: '68rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
              <h2
                style={{
                  fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                  fontWeight: 800,
                  letterSpacing: '-0.025em',
                  marginBottom: '0.875rem',
                  color: 'var(--color-text)',
                }}
              >
                Suporte completo a 8 classes de investimentos
              </h2>
              <p style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-muted)', maxWidth: '38rem', margin: '0 auto' }}>
                Do Tesouro Direto ao Bitcoin, consolide toda a sua estratégia financeira em uma única custódia inteligente.
              </p>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '1rem',
              }}
            >
              {ASSET_CLASSES.map((cls) => (
                <div
                  key={cls.name}
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.25rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.625rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span
                      style={{
                        fontSize: 'var(--text-2xs, 0.6875rem)',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: cls.color,
                      }}
                    >
                      {cls.type}
                    </span>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        fontWeight: 600,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '9999px',
                        background: 'oklch(from var(--color-text) l c h / 0.05)',
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      {cls.badge}
                    </span>
                  </div>

                  <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
                    {cls.name}
                  </h4>

                  <p style={{ fontSize: 'var(--text-xs)', lineHeight: 1.55, color: 'var(--color-text-muted)', margin: 0 }}>
                    {cls.desc}
                  </p>

                  <div
                    style={{
                      fontSize: 'var(--text-2xs, 0.6875rem)',
                      fontFamily: 'monospace',
                      color: 'var(--color-text-faint)',
                      paddingTop: '0.5rem',
                      borderTop: '1px solid oklch(from var(--color-text) l c h / 0.06)',
                      marginTop: 'auto',
                    }}
                  >
                    {cls.examples}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Segurança Institucional & Privacidade ── */}
        <section
          id="seguranca"
          style={{
            padding: '5rem clamp(1rem, 4vw, 3.5rem)',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
            background: 'oklch(from var(--color-surface) l c h / 0.4)',
          }}
        >
          <div style={{ maxWidth: '68rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
              <h2
                style={{
                  fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                  fontWeight: 800,
                  letterSpacing: '-0.025em',
                  marginBottom: '0.875rem',
                  color: 'var(--color-text)',
                }}
              >
                Segurança, privacidade e soberania do investidor
              </h2>
              <p style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-muted)', maxWidth: '36rem', margin: '0 auto' }}>
                Seus dados patrimoniais pertencem exclusivamente a você.
              </p>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '1.25rem',
              }}
            >
              <div
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '1.75rem',
                }}
              >
                <div style={{ color: 'var(--color-primary)', marginBottom: '1rem' }}>
                  <Lock size={28} />
                </div>
                <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
                  Autenticação em Dois Fatores (2FA)
                </h4>
                <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.6, color: 'var(--color-text-muted)', margin: 0 }}>
                  Suporte nativo a autenticadores TOTP (Google Authenticator, Apple Passwords, 1Password), impedindo acessos indevidos
                  mesmo em caso de vazamento de credenciais.
                </p>
              </div>

              <div
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '1.75rem',
                }}
              >
                <div style={{ color: 'var(--color-success)', marginBottom: '1rem' }}>
                  <ShieldCheck size={28} />
                </div>
                <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
                  Isolamento Rigoroso de Custódia
                </h4>
                <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.6, color: 'var(--color-text-muted)', margin: 0 }}>
                  Cada investidor opera em ambiente lógico restrito. Nenhum outro usuário ou serviço não autorizado tem visibilidade
                  sobre suas transações ou posições.
                </p>
              </div>

              <div
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '1.75rem',
                }}
              >
                <div style={{ color: 'var(--color-gold)', marginBottom: '1rem' }}>
                  <Sparkles size={28} />
                </div>
                <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
                  Zero Exposição de Saldos a Modelos de IA
                </h4>
                <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.6, color: 'var(--color-text-muted)', margin: 0 }}>
                  Nosso assistente de IA é estritamente fundamentado na documentação de ajuda e regras regulatórias. Seus saldos,
                  valores e notas nunca são enviados a servidores externos de terceiros.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section
          id="faq"
          style={{
            padding: '5rem clamp(1rem, 4vw, 3.5rem)',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          }}
        >
          <div style={{ maxWidth: '48rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
              <h2
                style={{
                  fontSize: 'clamp(1.75rem, 3.5vw, 2.25rem)',
                  fontWeight: 800,
                  letterSpacing: '-0.025em',
                  marginBottom: '0.75rem',
                  color: 'var(--color-text)',
                }}
              >
                Dúvidas frequentes
              </h2>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                Tudo o que você precisa saber sobre a governança e o funcionamento do SGI.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {FAQS.map((faq) => (
                <div
                  key={faq.q}
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '1.5rem',
                  }}
                >
                  <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
                    {faq.q}
                  </h4>
                  <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.65, color: 'var(--color-text-muted)', margin: 0 }}>
                    {faq.a}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Call to Action Imponente Final ── */}
        <section
          style={{
            padding: '5rem clamp(1rem, 4vw, 3.5rem) 6rem',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          }}
        >
          <div
            style={{
              maxWidth: '52rem',
              margin: '0 auto',
              textAlign: 'center',
              background: 'linear-gradient(180deg, oklch(from var(--color-primary) l c h / 0.12) 0%, transparent 100%)',
              border: '1px solid oklch(from var(--color-primary) l c h / 0.25)',
              borderRadius: 'var(--radius-2xl)',
              padding: ' clamp(2rem, 5vw, 4rem) clamp(1rem, 4vw, 3rem)',
              boxShadow: '0 20px 50px oklch(0 0 0 / 0.25)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem' }}>
              <LogoSGI size={52} iconOnly />
            </div>

            <h2
              style={{
                fontSize: 'clamp(1.85rem, 4vw, 2.75rem)',
                fontWeight: 800,
                letterSpacing: '-0.03em',
                marginBottom: '1rem',
                color: 'var(--color-text)',
              }}
            >
              Pronto para elevar o nível da gestão dos seus investimentos?
            </h2>

            <p
              style={{
                fontSize: 'var(--text-base)',
                lineHeight: 1.65,
                color: 'var(--color-text-muted)',
                maxWidth: '38rem',
                margin: '0 auto 2.5rem',
              }}
            >
              Crie sua conta no SGI em menos de um minuto e comece a acompanhar a evolução patrimonial com a precisão que seu
              patrimônio merece.
            </p>

            <Link
              to="/auth/registro"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.625rem',
                padding: '0.875rem 2.5rem',
                borderRadius: 'var(--radius-lg)',
                background: 'var(--color-primary)',
                color: 'var(--color-text-inverse)',
                fontSize: 'var(--text-base)',
                fontWeight: 650,
                textDecoration: 'none',
                boxShadow: '0 6px 20px oklch(from var(--color-primary) l c h / 0.35)',
                transition: 'transform 150ms ease, box-shadow 150ms ease',
              }}
            >
              Criar conta gratuita agora
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer
        style={{
          padding: '2.5rem clamp(1rem, 4vw, 3.5rem)',
          borderTop: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          background: 'var(--color-surface)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1.25rem',
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <LogoSGI size={24} />
          <span style={{ color: 'var(--color-text-faint)' }}>|</span>
          <span>Sistema de Gestão de Investimentos</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <Link to="/auth/login" style={{ color: 'inherit', textDecoration: 'none' }}>
            Entrar
          </Link>
          <Link to="/auth/registro" style={{ color: 'inherit', textDecoration: 'none' }}>
            Cadastrar
          </Link>
          <Link to="/carteira/ajuda" style={{ color: 'inherit', textDecoration: 'none' }}>
            Ajuda
          </Link>
        </div>

        <div style={{ color: 'var(--color-text-faint)' }}>
          © 2026 SGI - Sistema de Gestão de Investimentos. Todos os direitos reservados.
        </div>
      </footer>
    </div>
  )
}
