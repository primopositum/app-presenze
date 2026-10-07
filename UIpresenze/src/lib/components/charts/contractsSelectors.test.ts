import { describe, expect, it } from 'vitest';
import type { ContrattoCliente } from '$lib/services/clienti';
import type { ChartPoolTask } from '$lib/remo/chartsData';
import {
  blendedHourlyRate,
  contractProfitability,
  contractValueRows,
  contractsSummary,
  expiryRows,
  forecastByClient,
  forecastPoints,
  forecastStack,
  forecastUntilYearEnd,
  profitabilityList,
  signedByMonth,
  taskValueRows,
  tasksByKey
} from './contractsSelectors';

function contract(overrides: Partial<ContrattoCliente> = {}): ContrattoCliente {
  return {
    id: 1,
    contract_id: 'CTR-001',
    client_id: 1,
    client: { id: 1, nome: 'ACME', indirizzo: '', telefono: '' },
    value: '1000',
    current_value: '1300',
    pool_task: [],
    start_date: '2026-01-01',
    end_date: null,
    periodicity: {
      periodic_value: '300',
      period_days: 30,
      first_meeting_date: '2026-09-01',
      notification_days: 7
    },
    created_at: '',
    updated_at: '',
    ...overrides
  };
}

function task(key: string, seconds: number): ChartPoolTask {
  return { key, summary: `Task ${key}`, seconds };
}

describe('selettori contratti', () => {
  it('distingue valore iniziale e valore maturato senza trattare il secondo come residuo', () => {
    const summary = contractsSummary([contract()], new Date(2026, 8, 21));

    expect(summary.initialValue).toBe(1000);
    expect(summary.currentValue).toBe(1300);
    expect(summary.accruedValue).toBe(300);
    expect(summary.monthlyRecurring).toBe(300);
  });

  it('conta solo le scadenze ancora attive nella soglia indicata', () => {
    const today = new Date(2026, 8, 21);
    const expiring = contract({ id: 2, contract_id: 'CTR-EXP', end_date: '2026-10-01' });
    const expired = contract({ id: 3, contract_id: 'CTR-SCAD', end_date: '2026-09-20' });

    const summary = contractsSummary([expiring, expired], today, 30);

    expect(summary.active.map((item) => item.contract_id)).toEqual(['CTR-EXP']);
    expect(summary.expiring.map((item) => item.contract_id)).toEqual(['CTR-EXP']);
  });

  it('distribuisce gli incassi periodici nel mese in cui maturano', () => {
    const points = forecastPoints([contract()], new Date(2026, 8, 21), 3);

    expect(points.map((point) => point.value)).toEqual([0, 600, 300]);
  });

  it('si ferma al 31 dicembre dello stesso anno', () => {
    const points = forecastUntilYearEnd([contract()], new Date(2026, 9, 2));

    expect(points.map((point) => point.key)).toEqual(['2026-10', '2026-11', '2026-12']);
    expect(points.map((point) => point.value)).toEqual([300, 300, 300]);
  });

  it("conta i contratti firmati per mese di inizio, solo nell'anno indicato", () => {
    const points = signedByMonth(
      [
        contract({ id: 1, start_date: '2026-03-10' }),
        contract({ id: 2, start_date: '2026-03-28' }),
        contract({ id: 3, start_date: '2026-11-01' }),
        contract({ id: 4, start_date: '2025-03-15' })
      ],
      2026
    );

    expect(points).toHaveLength(12);
    expect(points[0].key).toBe('2026-01');
    expect(points.map((point) => point.value)).toEqual([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 1, 0]);
  });

  it('divide gli incassi per cliente e piega la coda in Altri', () => {
    const contracts = [1, 2, 3].map((id) =>
      contract({
        id,
        client_id: id,
        client: { id, nome: `Cliente ${id}`, indirizzo: '', telefono: '' },
        periodicity: {
          periodic_value: String(id * 100),
          period_days: 30,
          first_meeting_date: '2026-09-01',
          notification_days: 7
        }
      })
    );
    const byClient = forecastByClient(contracts, new Date(2026, 9, 2), 3);
    const stack = forecastStack(byClient, 2);

    expect(byClient.clients.map((client) => client.id)).toEqual(['3', '2', '1']);
    expect(stack.series.map((item) => item.id)).toEqual(['3', '__other__']);
    expect(stack.series[1].values).toEqual([300, 300, 300]);
    expect(stack.total).toBe(1800);
    expect(stack.fullLegend).toHaveLength(3);
    expect(stack.fullLegend[2].hint).toBe('in Altri (2)');
  });

  it('mette nel grafico per contratto il solo valore maturato', () => {
    const rows = contractValueRows([contract(), contract({ id: 2, contract_id: 'CTR-002', current_value: '500' })]);

    expect(rows.map((row) => row.value)).toEqual([1300, 500]);
    expect(rows[0].hint).toBe('ACME');
  });

  it('ordina le scadenze dalla piu vicina e segnala le urgenze', () => {
    const today = new Date(2026, 8, 21);
    const rows = expiryRows(
      [
        contract({ id: 1, contract_id: 'CTR-LONTANO', end_date: '2026-12-21' }),
        contract({ id: 2, contract_id: 'CTR-VICINO', end_date: '2026-10-01' })
      ],
      today
    );

    expect(rows.map((row) => row.label)).toEqual(['CTR-VICINO', 'CTR-LONTANO']);
    expect(rows[0].value).toBe(10);
  });
});

describe('redditivita dei contratti', () => {
  const pool = tasksByKey([task('ABC-1', 3600), task('ABC-2', 1800)]);

  it('ripartisce il valore del contratto fra le task in proporzione alle ore', () => {
    const row = contractProfitability(contract({ pool_task: ['ABC-1', 'ABC-2'] }), pool);

    expect(row.hours).toBe(1.5);
    expect(Math.round(row.hourlyRate)).toBe(867);
    expect(row.tasks.map((item) => Math.round(item.share))).toEqual([867, 433]);
  });

  it('conta le task del pool senza ore nel periodo senza falsare la tariffa', () => {
    const row = contractProfitability(contract({ pool_task: ['ABC-1', 'MANCANTE-9'] }), pool);

    expect(row.missingTasks).toBe(1);
    expect(row.poolSize).toBe(2);
    expect(row.hourlyRate).toBe(1300);
  });

  it('esclude dai grafici i contratti senza ore loggate', () => {
    const list = profitabilityList(
      [contract({ pool_task: ['ABC-1'] }), contract({ id: 2, contract_id: 'CTR-VUOTO', pool_task: [] })],
      pool
    );

    expect(list.map((row) => row.contractId)).toEqual(['CTR-001']);
  });

  it('usa una media ponderata sulle ore, non la media delle tariffe', () => {
    const list = profitabilityList(
      [
        contract({ id: 1, pool_task: ['ABC-1'], current_value: '1000' }),
        contract({ id: 2, contract_id: 'CTR-002', pool_task: ['ABC-2'], current_value: '100' })
      ],
      pool
    );

    // 1100 euro su 1,5 ore: la media semplice delle tariffe darebbe 600.
    expect(Math.round(blendedHourlyRate(list))).toBe(733);
  });

  it('somma il valore generato dalle task su tutti i contratti', () => {
    const list = profitabilityList([contract({ pool_task: ['ABC-1', 'ABC-2'] })], pool);
    const rows = taskValueRows(list);

    expect(rows.map((row) => row.label)).toEqual(['ABC-1', 'ABC-2']);
    expect(Math.round(rows[0].value + rows[1].value)).toBe(1300);
  });
});
