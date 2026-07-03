import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import KpiCard from '../KpiCard';

describe('KpiCard', () => {
  it('renders label and value', () => {
    render(
      <KpiCard 
        label="Total Investido" 
        value="R$ 100.000" 
      />
    );

    expect(screen.getByText('Total Investido')).toBeTruthy();
    expect(screen.getByText('R$ 100.000')).toBeTruthy();
  });

  it('renders change percentage when provided', () => {
    render(
      <KpiCard 
        label="Rentabilidade" 
        value="R$ 120.000" 
        change={5.5}
      />
    );

    expect(screen.getByText('+5.50%')).toBeTruthy();
  });

  it('renders subValue and subLabel when provided', () => {
    render(
      <KpiCard 
        label="Patrimônio" 
        value="R$ 150.000" 
        subValue="R$ 50.000" 
        subLabel="Ganho capital"
      />
    );

    expect(screen.getByText('R$ 50.000')).toBeTruthy();
    expect(screen.getByText('Ganho capital')).toBeTruthy();
  });

  it('handles null change gracefully', () => {
    const { container } = render(
      <KpiCard 
        label="Teste" 
        value="R$ 100" 
        change={null}
      />
    );

    expect(container.firstChild).toBeTruthy();
  });

  it('displays negative change with minus sign', () => {
    render(
      <KpiCard 
        label="Perdas" 
        value="R$ 90.000" 
        change={-3.25}
      />
    );

    expect(screen.getByText('-3.25%')).toBeTruthy();
  });
});
