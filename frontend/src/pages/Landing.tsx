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

// ── Logo ─────────────────────────────────────────────────────────────────────
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

// ── Dados ────────────────────────────────────────────────────────────────────
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

// ── Componentes internos ─────────────────────────────────────────────────────
function FeatureCard({ icon: Icon, title, desc }: (typeof FEATURES)[0]) {
  return (
    <div className="bg-surface border border-[var(--color-border)] rounded-xl p-6 flex flex-col gap-3 hover:shadow-md transition-shadow">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: 'oklch(from var(--color-primary) l c h / 0.1)' }}>
        <Icon size={20} color="var(--color-primary)" />
      </div>
      <h3 className="font-semibold text-base">{title}</h3>
      <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>{desc}</p>
    </div>
  )
}

function AssetChip({ label, color, example }: (typeof ASSET_TYPES)[0]) {
  return (
    <div className="flex items-center gap-2.5 bg-surface border border-[var(--color-border)] rounded-lg px-4 py-3">
      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{example}</p>
      </div>
    </div>
  )
}

// ── Página ───────────────────────────────────────────────────────────────────
export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-bg)', color: 'var(--color-text)' }}>

      {/* ── Navbar ── */}
      <header className="sticky top-0 z-30 flex items-center justify-between px-6 md:px-12 py-4
        border-b border-[var(--color-divider)] backdrop-blur-sm"
        style={{ background: 'oklch(from var(--color-bg) l c h / 0.92)' }}>
        <div className="flex items-center gap-2.5">
          <Logo size={32} />
          <span className="font-bold text-base tracking-tight">SIG v2</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/auth/login"
            className="text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Entrar
          </Link>
          <Link to="/auth/registro"
            className="btn btn-primary text-sm px-5 py-2"
          >
            Começar grátis
          </Link>
        </div>
      </header>

      <main className="flex-1">

        {/* ── Hero ── */}
        <section className="px-6 md:px-12 pt-20 pb-16 flex flex-col items-center text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-6 border"
            style={{
              background: 'oklch(from var(--color-primary) l c h / 0.08)',
              borderColor: 'oklch(from var(--color-primary) l c h / 0.2)',
              color: 'var(--color-primary)',
            }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--color-primary)' }} />
            Versão 2.0 — Agora com suporte a ativos internacionais
          </div>

          <h1 className="text-4xl md:text-5xl font-bold leading-tight max-w-2xl mb-5 tracking-tight">
            Toda a sua carteira de investimentos em um só lugar
          </h1>
          <p className="text-lg max-w-xl mb-10 leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
            Acompanhe rentabilidade, preço médio, proventos e evolução do patrimônio
            de todos os seus ativos — nacionais e internacionais.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <Link to="/auth/registro"
              className="btn btn-primary px-7 py-3 text-base flex items-center gap-2">
              Criar conta grátis
              <ArrowRight size={18} />
            </Link>
            <Link to="/auth/login"
              className="btn btn-secondary px-7 py-3 text-base flex items-center gap-2"
              style={{ border: '1px solid var(--color-border)' }}>
              Já tenho conta
              <ChevronRight size={18} />
            </Link>
          </div>
        </section>

        {/* ── Preview mockup ── */}
        <section className="px-6 md:px-12 pb-20 flex justify-center">
          <div className="w-full max-w-4xl rounded-2xl overflow-hidden border shadow-lg"
            style={{
              borderColor: 'var(--color-border)',
              background: 'var(--color-surface)',
              boxShadow: 'var(--shadow-lg)',
            }}>
            {/* Barra de janela */}
            <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: 'var(--color-divider)', background: 'var(--color-surface-offset)' }}>
              <span className="w-3 h-3 rounded-full" style={{ background: '#ff5f57' }} />
              <span className="w-3 h-3 rounded-full" style={{ background: '#febc2e' }} />
              <span className="w-3 h-3 rounded-full" style={{ background: '#28c840' }} />
              <span className="text-xs ml-2" style={{ color: 'var(--color-text-faint)' }}>SIG v2 — Carteira Principal</span>
            </div>

            {/* Dashboard preview */}
            <div className="p-6">
              {/* KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {[
                  { label: 'Patrimônio total',  value: 'R$ 87.432',  change: '+12,3%', pos: true },
                  { label: 'Rentabilidade',      value: '+R$ 9.621',  change: '+12,3%', pos: true },
                  { label: 'Proventos (ano)',    value: 'R$ 3.847',   change: '+8,1%',  pos: true },
                  { label: 'Variação hoje',      value: '-R$ 214',    change: '-0,24%', pos: false },
                ].map(k => (
                  <div key={k.label} className="kpi-card">
                    <span className="kpi-label">{k.label}</span>
                    <span className="kpi-value text-xl">{k.value}</span>
                    <span className={`kpi-change ${k.pos ? 'positive' : 'negative'}`}>{k.change}</span>
                  </div>
                ))}
              </div>

              {/* Tabela de posições */}
              <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
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
                      { ticker: 'PETR4',  type: 'acao',    qty: 200,  avg: 'R$ 32,40', cur: 'R$ 38,15', gain: '+17,7%', pos: true },
                      { ticker: 'MXRF11', type: 'fii',     qty: 500,  avg: 'R$ 10,12', cur: 'R$ 10,98', gain: '+8,5%',  pos: true },
                      { ticker: 'IVVB11', type: 'etf',     qty: 15,   avg: 'R$ 312,00',cur: 'R$ 341,20',gain: '+9,4%',  pos: true },
                      { ticker: 'BTC',    type: 'cripto',  qty: 0.12, avg: 'R$ 298k',  cur: 'R$ 342k',  gain: '+14,8%', pos: true },
                    ].map(r => (
                      <tr key={r.ticker}>
                        <td className="flex items-center gap-2">
                          <span className="font-semibold">{r.ticker}</span>
                          <span className={`asset-badge ${r.type}`}>{r.type}</span>
                        </td>
                        <td>{r.qty}</td>
                        <td>{r.avg}</td>
                        <td>{r.cur}</td>
                        <td className={r.pos ? 'text-green-600 dark:text-green-400 font-medium' : 'text-red-500 font-medium'}>{r.gain}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* ── Tipos de ativos ── */}
        <section className="px-6 md:px-12 py-16 border-t" style={{ borderColor: 'var(--color-divider)' }}>
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-2xl font-bold mb-3">Suporte a todos os tipos de ativo</h2>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Do Tesouro Direto ao Bitcoin, tudo em uma única plataforma.
              </p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {ASSET_TYPES.map(a => <AssetChip key={a.label} {...a} />)}
            </div>
          </div>
        </section>

        {/* ── Features ── */}
        <section className="px-6 md:px-12 py-16 border-t" style={{ borderColor: 'var(--color-divider)' }}>
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-2xl font-bold mb-3">Tudo que você precisa para acompanhar seus investimentos</h2>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Funcionalidades pensadas para o investidor brasileiro.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {FEATURES.map(f => <FeatureCard key={f.title} {...f} />)}
            </div>
          </div>
        </section>

        {/* ── CTA final ── */}
        <section className="px-6 md:px-12 py-20 border-t" style={{ borderColor: 'var(--color-divider)' }}>
          <div className="max-w-lg mx-auto text-center">
            <Logo size={48} />
            <h2 className="text-2xl font-bold mt-6 mb-3">Pronto para organizar seus investimentos?</h2>
            <p className="text-sm mb-8" style={{ color: 'var(--color-text-muted)' }}>
              Crie sua conta, cadastre suas carteiras e comece a acompanhar sua evolução patrimonial agora mesmo.
            </p>
            <Link to="/auth/registro" className="btn btn-primary px-8 py-3 text-base inline-flex items-center gap-2">
              Começar agora — é grátis
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="px-6 md:px-12 py-6 border-t flex items-center justify-between text-xs"
        style={{ borderColor: 'var(--color-divider)', color: 'var(--color-text-faint)' }}>
        <span>© 2026 SIG v2 — Sistema de Gestão de Investimentos</span>
        <div className="flex items-center gap-2">
          <Logo size={20} />
        </div>
      </footer>
    </div>
  )
}
