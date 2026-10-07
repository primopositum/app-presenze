import { describe, expect, it } from 'vitest';
import type { ContrattoCliente } from '$lib/services/clienti';
import { resolveValues } from '../core/filterState';
import type { FilterValues } from '../core/types';
import { applyContrattiFilters, contractStatus, contrattiDisplay, contrattiFilters } from './apply';

const base = {
  id: 1,
  contract_id: 'CTR-001',
  client_id: 1,
  client: { id: 1, nome: 'ACME', indirizzo: '', telefono: '' },
  value: '1000',
  current_value: '1300',
  pool_task: [],
  start_date: '2026-01-01',
  end_date: null,
  periodicity: null,
  created_at: '',
  updated_at: ''
} as ContrattoCliente;

const recurring = {
  ...base,
  id: 2,
  contract_id: 'CTR-002',
  client_id: 2,
  end_date: '2026-06-30',
  periodicity: {
    periodic_value: '300',
    period_days: 30,
    first_meeting_date: '2026-01-01',
    notification_days: 7
  }
} as ContrattoCliente;

const reference = new Date(2026, 8, 23);
const values = (changes: FilterValues) => resolveValues(contrattiFilters, changes);

describe('filtri Contratti', () => {
  it('stato rispetto alla data di riferimento', () => {
    expect(contractStatus(base, reference)).toBe('active');
    expect(contractStatus(recurring, reference)).toBe('expired');
  });

  it('fatturazione, stato, scadenza e valore', () => {
    const all = [base, recurring];
    expect(applyContrattiFilters(all, values({ billing: 'recurring' }), reference)).toEqual([recurring]);
    expect(applyContrattiFilters(all, values({ status: ['active'] }), reference)).toEqual([base]);
    expect(applyContrattiFilters(all, values({ endMode: 'open' }), reference)).toEqual([base]);
    expect(
      applyContrattiFilters(all, values({ currentValue: { min: 2000, max: null } }), reference)
    ).toEqual([]);
  });
});

describe('impostazioni di visualizzazione Contratti', () => {
  const defaults = { referenceDate: new Date(2026, 9, 2), expiringDays: 90, forecastMonths: 12, topCount: 12 };

  it("usa l'anno della data di riferimento finche' non se ne sceglie uno", () => {
    expect(contrattiDisplay({}, defaults).signedYear).toBe(2026);
    expect(contrattiDisplay({ referenceDate: '2024-05-10' }, defaults).signedYear).toBe(2024);
    expect(contrattiDisplay({ signedYear: '2025' }, defaults).signedYear).toBe(2025);
  });
});
