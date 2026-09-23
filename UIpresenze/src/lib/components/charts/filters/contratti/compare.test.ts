import { describe, expect, it } from 'vitest';
import type { ContrattoCliente } from '$lib/services/clienti';
import { compareContract } from './compare';

function contract(id: number, value: string): ContrattoCliente {
  return {
    id,
    contract_id: `CTR-${id}`,
    client_id: id,
    client: { id, nome: `Cliente ${id}`, indirizzo: '', telefono: '' },
    value,
    current_value: value,
    pool_task: [],
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    periodicity: null,
    created_at: '',
    updated_at: ''
  } as ContrattoCliente;
}

const options = { referenceDate: new Date(2026, 8, 23), forecastMonths: 12, topCount: 10 };

describe('confronto contratti', () => {
  const all = [contract(1, '1000'), contract(2, '500'), contract(3, '500')];

  it('indice, posizione e quota rispetto agli altri filtrati', () => {
    const result = compareContract(all, all, '1', options);
    expect(result?.standing.rank).toBe(1);
    expect(result?.share).toBe(0.5);
    expect(result?.index.find((row) => row.id === 'current')?.value).toBe(200);
    expect(result?.daysLeft).toBe(99);
  });

  it('il contratto escluso dai filtri resta confrontabile', () => {
    const result = compareContract(all, all.slice(1), '1', options);
    expect(result?.inScope).toBe(false);
    expect(result?.others).toBe(2);
    expect(result?.ranking[0].id).toBe('1');
  });

  it('null se il contratto non esiste', () => {
    expect(compareContract(all, all, '99', options)).toBeNull();
  });
});
