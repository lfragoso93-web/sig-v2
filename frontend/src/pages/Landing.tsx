import { Link } from 'react-router-dom'
import {
  TrendingUp,
  Wallet,
  Gift,
  Globe,
  ShieldCheck,
  BarChart2,
  ArrowRight,
  ChevronRight,
} from 'lucide-react'

// ── Logo ────────────────────────────────────────────────────────────────────────────────────
function Logo({ size = 40 }: { size?: number }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-label="SIG v2" style={{ width: size, height: size }}>
      <rect width="40" height="40" rx="10" fill="var(--color-primary)" />
      <polyline
        points="7,28 16,18 22,23 33,11"
        stroke="white" strokeWidth="3"
        strokeLinecap="round" strokeLinejoin="round" fill="none"
      />
      <circle cx="33" cy="11" r="2.5" fill="white" />
    </svg>
  )
}

// ── Dados ────────────────────────────────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: Wallet,
    title: 'Multi-carteiras',
    desc: 'Organize seus ativos em carteiras separadas — previdência, dividendos, growth — e acompanhe cada uma de forma independente.',
  },
  {
    icon: TrendingUp,
    title: 'Rentabilidade real',
    desc: 'Preço médio, ganho realizado e não-realizado calculados automaticamente a cada nova transação registrada.',
  },
  {
    icon: Gift,
    title: 'Proventos & dividendos',
    desc: 'Histórico completo de dividendos, JCP e rendimentos recebidos. Projeção de proventos futuros com base no histórico.',
  },
  {
    icon: Globe,
    title: 'Ativos nacionais & globais',
    desc: 'Ações, FIIs, ETFs, Tesouro Direto, Renda Fixa, Stocks americanas, ETFs internacionais e criptomoedas em um só lugar.',
  },
  {
    icon: BarChart2,
    title: 'Evolução do patrimônio',
    desc: 'Gráficos de evolução histórica da carteira, alocação por tipo de ativo e comparativo de performance.',
  },
  {
    icon: ShieldCheck,
    title: 'Seguro e multi-usuário',
    desc: 'Cada usuário tem acesso exclusivo às suas carteiras. Autenticação JWT com token seguro por sessão.',
  },
]

const ASSET_TYPES = [
  { label: 'Ações',           color: 'var(--color-blue)',    example: 'PETR4, VALE3' },
  { label: 'FIIs',            color: 'var(--color-gold)',    example: 'MXRF11, HGLG11' },
  { label: 'ETFs Nacionais',  color: 'var(--color-purple)',  example: 'BOVA11, IVVB11' },
  { label: 'Tesouro Direto',  color: 'var(--color-success)', example: 'IPCA+, Selic' },
  { label: 'Stocks',          color: 'var(--color-primary)', example: 'AAPL, MSFT' },
  { label: 'ETFs Internac.',  color: 'var(--color-blue)',    example: 'QQQ, SPY' },
  { label: 'Criptomoedas',    color: 'var(--color-orange)',  example: 'BTC, ETH' },
  { label: 'Renda Fixa',      color: 'var(--color-warning)', example: 'CDB, LCI' },
]

// ── Componentes internos ───────────────────────────────────────────────────────────────────────────
function FeatureCard({ icon: Icon, title, desc }: (typeof FEATURES)[0]) {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-xl)',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        transition: 'box-shadow 150ms ease',
      }}
    >
      <div style={{
        width: 40, height: 40,
        borderRadius: 'var(--radius-lg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'oklch(from var(--color-primary) l c h / 0.1)',
      }}>
        <Icon size={20} color="var(--color-primary)" />
      </div>
      <h3 style={{ fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--color-text)' }}>{title}</h3>
      <p style={{ fontSize: 'var(--text-sm)', lineHeight: 1.6, color: 'var(--color-text-muted)' }}>{desc}</p>
    </div>
  )
}

function AssetChip({ label, color, example }: (typeof ASSET_TYPES)[0]) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.625rem',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding: '0.75rem 1rem',
    }}>
      <span style={{ width: 10, height: 10, borderRadius: '9999px', flexShrink: 0, background: color }} />
      <div>
        <p style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--color-text)' }}>{label}</p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>{example}</p>
      </div>
    </div>
  )
}

// ── Página ────────────────────────────────────────────────────────────────────────────────────
export default function Landing() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--color-bg)', color: 'var(--color-text)' }}>

      {/* ── Navbar ── */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 30,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '1rem 3rem',
        borderBottom: '1px solid var(--color-divider)',
        backdropFilter: 'blur(8px)',
        background: 'oklch(from var(--color-bg) l c h / 0.92)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <Logo size={32} />
          <span style={{ fontWeight: 700, fontSize: 'var(--text-base)', letterSpacing: '-0.02em', color: 'var(--color-text)' }}>SIG v2</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link to="/auth/login"
            style={{
              fontSize: 'var(--text-sm)', fontWeight: 500,
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-lg)',
              color: 'var(--color-text-muted)',
              textDecoration: 'none',
              transition: 'color 150ms ease',
            }}
          >
            Entrar
          </Link>
          <Link to="/auth/registro"
            style={{
              fontSize: 'var(--text-sm)', fontWeight: 500,
              padding: '0.5rem 1.25rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              textDecoration: 'none',
              transition: 'background 150ms ease',
            }}
          >
            Começar grátis
          </Link>
        </div>
      </header>

      <main style={{ flex: 1 }}>

        {/* ── Hero ── */}
        <section style={{
          padding: '5rem 3rem 4rem',
          display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.375rem 0.75rem',
            borderRadius: '9999px',
            fontSize: 'var(--text-xs)', fontWeight: 500,
            marginBottom: '1.5rem',
            border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
            background: 'oklch(from var(--color-primary) l c h / 0.08)',
            color: 'var(--color-primary)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '9999px', background: 'var(--color-primary)', animation: 'pulse 2s infinite' }} />
            Versão 2.0 — Agora com suporte a ativos internacionais
          </div>

          <h1 style={{
            fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 700,
            lineHeight: 1.2, maxWidth: '40rem',
            marginBottom: '1.25rem', letterSpacing: '-0.02em',
            color: 'var(--color-text)',
          }}>
            Toda a sua carteira de investimentos em um só lugar
          </h1>
          <p style={{
            fontSize: 'var(--text-lg)', maxWidth: '36rem',
            marginBottom: '2.5rem', lineHeight: 1.6,
            color: 'var(--color-text-muted)',
          }}>
            Acompanhe rentabilidade, preço médio, proventos e evolução do patrimônio
            de todos os seus ativos — nacionais e internacionais.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'center' }}>
            <Link to="/auth/registro" style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 1.75rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              fontSize: 'var(--text-base)', fontWeight: 500,
              textDecoration: 'none',
              transition: 'background 150ms ease',
            }}>
              Criar conta grátis
              <ArrowRight size={18} />
            </Link>
            <Link to="/auth/login" style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 1.75rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-surface)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)',
              fontSize: 'var(--text-base)', fontWeight: 500,
              textDecoration: 'none',
              transition: 'background 150ms ease',
            }}>
              Já tenho conta
              <ChevronRight size={18} />
            </Link>
          </div>
        </section>

        {/* ── Preview mockup ── */}
        <section style={{ padding: '0 3rem 5rem', display: 'flex', justifyContent: 'center' }}>
          <div style={{
            width: '100%', maxWidth: '56rem',
            borderRadius: 'var(--radius-xl)',
            overflow: 'hidden',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            boxShadow: 'var(--shadow-lg)',
          }}>
            {/* Barra de janela */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--color-divider)',
              background: 'var(--color-surface-offset)',
            }}>
              <span style={{ width: 12, height: 12, borderRadius: '9999px', background: '#ff5f57' }} />
              <span style={{ width: 12, height: 12, borderRadius: '9999px', background: '#febc2e' }} />
              <span style={{ width: 12, height: 12, borderRadius: '9999px', background: '#28c840' }} />
              <span style={{ fontSize: 'var(--text-xs)', marginLeft: '0.5rem', color: 'var(--color-text-faint)' }}>SIG v2 — Carteira Principal</span>
            </div>

            {/* Dashboard preview */}
            <div style={{ padding: '1.5rem' }}>
              {/* KPIs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
                {[
                  { label: 'Patrimônio total',  value: 'R$ 87.432',  change: '+12,3%', pos: true },
                  { label: 'Rentabilidade',      value: '+R$ 9.621',  change: '+12,3%', pos: true },
                  { label: 'Proventos (ano)',    value: 'R$ 3.847',   change: '+8,1%',  pos: true },
                  { label: 'Variação hoje',      value: '-R$ 214',    change: '-0,24%', pos: false },
                ].map(k => (
                  <div key={k.label} className="kpi-card">
                    <span className="kpi-label">{k.label}</span>
                    <span className="kpi-value" style={{ fontSize: 'var(--text-xl)' }}>{k.value}</span>
                    <span className={`kpi-change ${k.pos ? 'positive' : 'negative'}`}>{k.change}</span>
                  </div>
                ))}
              </div>

              {/* Tabela de posições */}
              <div style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
                <table className="positions-table">
                  <thead style={{ background: 'var(--color-surface-offset)' }}>
                    <tr>
                      <th>Ativo</th>
                      <th>Qtd</th>
                      <th>Preço médio</th>
                      <th>Preço atual</th>
                      <th>Rentab.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { ticker: 'PETR4',  type: 'acao',   qty: 200,  avg: 'R$ 32,40', cur: 'R$ 38,15', gain: '+17,7%', pos: true },
                      { ticker: 'MXRF11', type: 'fii',    qty: 500,  avg: 'R$ 10,12', cur: 'R$ 10,98', gain: '+8,5%',  pos: true },
                      { ticker: 'IVVB11', type: 'etf',    qty: 15,   avg: 'R$ 312,00',cur: 'R$ 341,20',gain: '+9,4%',  pos: true },
                      { ticker: 'BTC',    type: 'cripto', qty: 0.12, avg: 'R$ 298k',  cur: 'R$ 342k',  gain: '+14,8%', pos: true },
                    ].map(r => (
                      <tr key={r.ticker}>
                        <td style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{r.ticker}</span>
                          <span className={`asset-badge ${r.type}`}>{r.type}</span>
                        </td>
                        <td>{r.qty}</td>
                        <td>{r.avg}</td>
                        <td>{r.cur}</td>
                        <td style={{ color: r.pos ? 'var(--color-success)' : 'var(--color-notification)', fontWeight: 500 }}>{r.gain}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* ── Tipos de ativos ── */}
        <section style={{
          padding: '4rem 3rem',
          borderTop: '1px solid var(--color-divider)',
        }}>
          <div style={{ maxWidth: '56rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--color-text)' }}>Suporte a todos os tipos de ativo</h2>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                Do Tesouro Direto ao Bitcoin, tudo em uma única plataforma.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
              {ASSET_TYPES.map(a => <AssetChip key={a.label} {...a} />)}
            </div>
          </div>
        </section>

        {/* ── Features ── */}
        <section style={{
          padding: '4rem 3rem',
          borderTop: '1px solid var(--color-divider)',
        }}>
          <div style={{ maxWidth: '56rem', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--color-text)' }}>Tudo que você precisa para acompanhar seus investimentos</h2>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                Funcionalidades pensadas para o investidor brasileiro.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
              {FEATURES.map(f => <FeatureCard key={f.title} {...f} />)}
            </div>
          </div>
        </section>

        {/* ── CTA final ── */}
        <section style={{
          padding: '5rem 3rem',
          borderTop: '1px solid var(--color-divider)',
        }}>
          <div style={{ maxWidth: '32rem', margin: '0 auto', textAlign: 'center' }}>
            <Logo size={48} />
            <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginTop: '1.5rem', marginBottom: '0.75rem', color: 'var(--color-text)' }}>Pronto para organizar seus investimentos?</h2>
            <p style={{ fontSize: 'var(--text-sm)', marginBottom: '2rem', color: 'var(--color-text-muted)' }}>
              Crie sua conta, cadastre suas carteiras e comece a acompanhar sua evolução patrimonial agora mesmo.
            </p>
            <Link to="/auth/registro" style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 2rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              fontSize: 'var(--text-base)', fontWeight: 500,
              textDecoration: 'none',
              transition: 'background 150ms ease',
            }}>
              Começar agora — é grátis
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer style={{
        padding: '1.5rem 3rem',
        borderTop: '1px solid var(--color-divider)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: 'var(--text-xs)',
        color: 'var(--color-text-faint)',
      }}>
        <span>© 2026 SIG v2 — Sistema de Gestão de Investimentos</span>
        <Logo size={20} />
      </footer>
    </div>
  )
}
