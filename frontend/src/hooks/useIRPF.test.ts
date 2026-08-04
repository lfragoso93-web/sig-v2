import { describe, expect, it } from 'vitest'

import { toIRPFReportView } from './useIRPF'
import type { IRPFReportOut } from '@/types/irpf'

const report: IRPFReportOut = {
  portfolio_id: 7,
  ano: 2024,
  bens_direitos: [],
  ganhos_mensais: [],
  dividendos: [],
  jcp: [],
  resumo: {
    ano: 2024,
    total_bens_direitos: 0,
    total_vendas_ano: 0,
    lucro_tributavel_swing: 0,
    lucro_tributavel_day_trade: 0,
    ir_swing_trade_devido: 0,
    ir_day_trade_devido: 0,
    ir_retido_fonte_total: 0,
    ir_a_recolher_total: 0,
    total_dividendos_isentos: 0,
    total_jcp_bruto: 0,
    total_jcp_ir_retido: 0,
    prejuizo_acumulado: 0,
  },
}

describe('toIRPFReportView', () => {
  it('maps canonical report fields to the page view model', () => {
    const view = toIRPFReportView(report)

    expect(view.portfolio_id).toBe(7)
    expect(view.ganhos_capital).toBe(report.ganhos_mensais)
    expect(view.rendimentos_isentos).toBe(report.dividendos)
    expect('ganhos_mensais' in view).toBe(false)
    expect('dividendos' in view).toBe(false)
  })
})
