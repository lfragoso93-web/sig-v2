/**
 * RentabilidadeChart
 * Gráfico de retorno % mês a mês da carteira com linhas de benchmark.
 *
 * Dados da carteira: useMonthlyEvolution (field: return_pct)
 * Benchmark:
 *   - IBOV: histórico mensal via BRAPI (/quote/^BVSP/historical)
 *   - CDI:  taxa anual do BCB (endpoint 12/últimos, divisão simples por 12)
 *   - IPCA: índice mensal do BCB (endpoint 433)
 *
 * A comparação usa retorno acumulado indexado a 100 no primeiro mês do período.
 */
import { useState, useEffect } from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { useMonthlyEvolution, type PeriodOption } from '@/hooks/useEvolution'

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface BenchmarkPoint {
  date: string  // YYYY-MM
  ibov?: number // retorno % mensal
  cdi?:  number
  ipca?: number
}

interface ChartPoint {
  label:     string  // "Jan/25"
  carteira:  number  // return_pct do mês
  ibov?:     number
  cdi?:      number
  ipca?:     number
}

// ── Fetch benchmarks via APIs públicas ──────────────────────────────────────────────

async function fetchIbovMonthly(_months: number): Promise<Record<string, number>> {
  try {
    const url = `https://brapi.dev/api/quote/%5EBVSP?range=2y&interval=1mo&fundamental=false`
    const res = await fetch(url)
    const json = await res.json()
    const hist: { date: string; adjustedClose: number }[] =
      json?.results?.[0]?.historicalDataPrice ?? []
    const map: Record<string, number> = {}
    // calcular retorno % mês a mês
    for (let i = 1; i < hist.length; i++) {
      const prev = hist[i - 1].adjustedClose
      const curr = hist[i].adjustedClose
      if (!prev) continue
      const ym = hist[i].date.slice(0, 7) // YYYY-MM
      map[ym] = ((curr - prev) / prev) * 100
    }
    return map
  } catch {
    return {}
  }
}

async function fetchCdiMonthly(months: number): Promise<Record<string, number>> {
  try {
    // BCB série 4391 = CDI Over acumulado no mês (%)
    const url = `https://api.bcb.gov.br/dados/serie/bcdata.sgs.4391/dados/ultimos/${months + 2}?formato=json`
    const res = await fetch(url)
    const json: { data: string; valor: string }[] = await res.json()
    const map: Record<string, number> = {}
    for (const p of json) {
      // data vem como DD/MM/YYYY
      const [_d, m, y] = p.data.split('/')
      const ym = `${y}-${m.padStart(2, '0')}`
      map[ym] = parseFloat(p.valor)
    }
    return map
  } catch {
    return {}
  }
}

async function fetchIpcaMonthly(months: number): Promise<Record<string, number>> {
  try {
    // BCB série 433 = IPCA variação mensal (%)
    const url = `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/${months + 2}?formato=json`
    const res = await fetch(url)
    const json: { data: string; valor: string }[] = await res.json()
    const map: Record<string, number> = {}
    for (const p of json) {
      const [_d, m, y] = p.data.split('/')
      const ym = `${y}-${m.padStart(2, '0')}`
      map[ym] = parseFloat(p.valor)
    }
    return map
  } catch {
    return {}
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────────────

const MONTH_SHORT = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

function ymToLabel(ym: string): string {
  const [y, m] = ym.split('-')
  return `${MONTH_SHORT[parseInt(m) - 1]}/${y.slice(2)}`
}

function pct(v: number) {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

const PERIOD_OPTIONS: { label: string; value: PeriodOption }[] = [
  { label: '6 meses',   value: '6m'  },
  { label: '12 meses',  value: '12m' },
  { label: '24 meses',  value: '24m' },
  { label: 'Todo período', value: 'all' },
]

const PERIOD_MONTHS: Record<PeriodOption, number> = {
  '6m': 6, '12m': 12, '24m': 24, 'all': 120,
}

// ── Tooltip customizado ───────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--color-surface-2)',
      border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
      borderRadius: 'var(--radius-md)',
      padding: '8px 12px',
      fontSize: 'var(--text-xs)',
      boxShadow: '0 4px 12px oklch(0 0 0 / 0.15)',
      minWidth: 140,
    }}>
      <p style={{ fontWeight: 700, color: 'var(--color-text)', marginBottom: 6 }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, color: p.color }}>
          <span>{p.name}</span>
          <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {p.value != null ? pct(p.value) : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────────────────

export default function RentabilidadeChart({ portfolioId }: { portfolioId: number }) {
  const [period,     setPeriod]     = useState<PeriodOption>('12m')
  const [benchmarks, setBenchmarks] = useState<BenchmarkPoint[]>([])
  const [loading,    setLoading]    = useState(false)
  const [showIbov,   setShowIbov]   = useState(true)
  const [showCdi,    setShowCdi]    = useState(true)
  const [showIpca,   setShowIpca]   = useState(false)

  const months = PERIOD_MONTHS[period]
  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)

  // Busca benchmarks quando o período muda
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      fetchIbovMonthly(months),
      fetchCdiMonthly(months),
      fetchIpcaMonthly(months),
    ]).then(([ibovMap, cdiMap, ipcaMap]) => {
      if (cancelled) return
      // Unir todos os meses conhecidos
      const allYm = new Set([...Object.keys(ibovMap), ...Object.keys(cdiMap), ...Object.keys(ipcaMap)])
      const pts: BenchmarkPoint[] = Array.from(allYm)
        .sort()
        .map(ym => ({ date: ym, ibov: ibovMap[ym], cdi: cdiMap[ym], ipca: ipcaMap[ym] }))
      setBenchmarks(pts)
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [months])

  // Merge carteira + benchmarks por mês YYYY-MM
  const chartData: ChartPoint[] = (monthly ?? []).map(p => {
    const ym = p.date.slice(0, 7)
    const bm = benchmarks.find(b => b.date === ym)
    return {
      label:    ymToLabel(ym),
      carteira: p.return_pct,
      ibov:     bm?.ibov,
      cdi:      bm?.cdi,
      ipca:     bm?.ipca,
    }
  })

  const isLoading = loadingMonthly || loading

  return (
    <div className="card p-4">
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem',
      }}>
        <span className="section-card-title">Rentabilidade mensal</span>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* Toggles de benchmark */}
          {([
            { key: 'ibov', label: 'IBOV', show: showIbov, toggle: () => setShowIbov(v => !v), color: '#f59e0b' },
            { key: 'cdi',  label: 'CDI',  show: showCdi,  toggle: () => setShowCdi(v => !v),  color: '#6366f1' },
            { key: 'ipca', label: 'IPCA', show: showIpca, toggle: () => setShowIpca(v => !v), color: '#10b981' },
          ] as const).map(b => (
            <button
              key={b.key}
              onClick={b.toggle}
              style={{
                fontSize: 'var(--text-xs)', fontWeight: 600,
                padding: '2px 10px',
                borderRadius: 'var(--radius-full)',
                border: `1px solid ${b.show ? b.color : 'oklch(from var(--color-text) l c h / 0.12)'}`,
                background: b.show ? `${b.color}1a` : 'transparent',
                color: b.show ? b.color : 'var(--color-text-faint)',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {b.label}
            </button>
          ))}

          {/* Seletor de período */}
          <div style={{ display: 'flex', gap: 4 }}>
            {PERIOD_OPTIONS.map(o => (
              <button
                key={o.value}
                onClick={() => setPeriod(o.value)}
                style={{
                  fontSize: 'var(--text-xs)', fontWeight: 600,
                  padding: '2px 10px',
                  borderRadius: 'var(--radius-full)',
                  border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
                  background: period === o.value
                    ? 'oklch(from var(--color-primary) l c h / 0.12)'
                    : 'transparent',
                  color: period === o.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Gráfico */}
      {isLoading ? (
        <div
          className="animate-pulse rounded-lg"
          style={{ height: 260, background: 'var(--color-surface-offset)' }}
        />
      ) : chartData.length === 0 ? (
        <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
            Sem dados para o período selecionado
          </span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="oklch(from var(--color-text) l c h / 0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: 'var(--color-text-faint)' }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={v => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
              tick={{ fontSize: 10, fill: 'var(--color-text-faint)' }}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="oklch(from var(--color-text) l c h / 0.15)" strokeWidth={1} />

            {/* Barras da carteira */}
            <Bar
              dataKey="carteira"
              name="Carteira"
              radius={[3, 3, 0, 0]}
              maxBarSize={32}
              fill="var(--color-primary)"
              label={false}
            />

            {/* Linhas de benchmark */}
            {showIbov && (
              <Line
                dataKey="ibov"
                name="IBOV"
                type="monotone"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            )}
            {showCdi && (
              <Line
                dataKey="cdi"
                name="CDI"
                type="monotone"
                stroke="#6366f1"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                connectNulls
              />
            )}
            {showIpca && (
              <Line
                dataKey="ipca"
                name="IPCA"
                type="monotone"
                stroke="#10b981"
                strokeWidth={1.5}
                strokeDasharray="2 2"
                dot={false}
                connectNulls
              />
            )}

            <Legend
              iconType="plainline"
              iconSize={12}
              wrapperStyle={{ fontSize: 'var(--text-xs)', paddingTop: 8 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* Nota de rodapé */}
      <p style={{ fontSize: '0.65rem', color: 'var(--color-text-faint)', marginTop: 4, textAlign: 'right' }}>
        Carteira: retorno % mensal do patrimônio · IBOV: BRAPI · CDI: BCB série 4391 · IPCA: BCB série 433
      </p>
    </div>
  )
}
