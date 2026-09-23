import { describe, expect, it } from 'vitest';
import { activeCount, screenDefaults } from './filterState';
import { compileRegex, inDates, inRange, keyList } from './primitives';
import { contrattiFilters } from '../contratti/apply';

describe('mattoncini', () => {
  it('range con estremi vuoti non limita', () => {
    expect(inRange({ min: null, max: null }, 10)).toBe(true);
    expect(inRange({ min: 1, max: null }, 3599, 3600)).toBe(false);
    expect(inRange({ min: null, max: 2 }, 7200, 3600)).toBe(true);
  });

  it('intervallo di date inclusivo sugli estremi', () => {
    expect(inDates({ from: '2026-01-01', to: '2026-01-31' }, '2026-01-31T10:00:00')).toBe(true);
    expect(inDates({ from: '2026-01-01', to: '' }, '2025-12-31')).toBe(false);
    expect(inDates({ from: '2026-01-01', to: '' }, null)).toBe(false);
  });

  it('regex non valida viene ignorata', () => {
    expect(compileRegex('([')).toBeNull();
    expect(compileRegex('^abc')?.test('ABC-1')).toBe(true);
  });

  it('elenco di chiavi normalizzato', () => {
    expect([...keyList('abc-1, ABC-2;abc-3')]).toEqual(['ABC-1', 'ABC-2', 'ABC-3']);
  });
});

describe('stato dei filtri', () => {
  it('i default non contano come filtri attivi', () => {
    expect(activeCount(contrattiFilters, screenDefaults(contrattiFilters))).toBe(0);
    expect(activeCount(contrattiFilters, { billing: 'recurring', clients: ['1'] })).toBe(2);
  });
});
