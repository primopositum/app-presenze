import { describe, it, expect } from 'vitest';
import {
  addGrouped,
  barLayout,
  barPath,
  buildChartRows,
  niceTicks,
  topRows,
  withOther,
  type ChartGroups
} from './chartData';
import { BAR_SIZING, resolveRenderMode, truncateToWidth } from './chartSizing';
import { NEUTRAL, SERIES } from './palette';

function rows(values: number[], label = (index: number) => `Contratto ${index}`) {
  const groups: ChartGroups = {};
  values.forEach((value, index) => addGrouped(groups, `c${index}`, label(index), value));
  return buildChartRows(groups);
}

describe('righe dei grafici', () => {
  it('ordina per valore e calcola le percentuali', () => {
    const built = rows([1000, 3000]);

    expect(built.map((row) => row.id)).toEqual(['c1', 'c0']);
    expect(built[0].percent).toBe(75);
  });

  it('scarta le voci a zero se non richiesto', () => {
    expect(rows([0, 500])).toHaveLength(1);
  });

  it('da una tinta sola ai grafici di magnitudine', () => {
    const built = rows([300, 200, 100]);

    expect(new Set(built.map((row) => row.color)).size).toBe(1);
  });

  it('assegna la scala categorica in ordine, solo quando le voci sono il soggetto', () => {
    const groups: ChartGroups = {};
    addGrouped(groups, 'a', 'A', 300);
    addGrouped(groups, 'b', 'B', 200);

    const built = buildChartRows(groups, { palette: 'identity' });

    expect(built.map((row) => row.color)).toEqual([SERIES[0], SERIES[1]]);
  });
});

describe('coda ripiegata su Altri', () => {
  it('lascia intatte le righe quando stanno nel limite', () => {
    const built = rows([5, 4, 3]);

    expect(withOther(built, 6)).toEqual(built);
  });

  it('somma la coda in una sola voce neutra senza perdere il totale', () => {
    const built = rows([10, 8, 6, 4, 2]);
    const folded = withOther(built, 3);

    expect(folded).toHaveLength(3);
    expect(folded[2].value).toBe(6 + 4 + 2);
    expect(folded[2].color).toBe(NEUTRAL);
    expect(folded.reduce((sum, row) => sum + row.value, 0)).toBe(30);
  });

  it('taglia le classifiche senza toccarle se sono gia corte', () => {
    const built = rows([3, 2, 1]);

    expect(topRows(built, 2)).toHaveLength(2);
    expect(topRows(built, 9)).toBe(built);
  });
});

describe('tacche degli assi', () => {
  it('arrotonda a passi leggibili che coprono il massimo', () => {
    const ticks = niceTicks(3700, 4);

    expect(ticks[0]).toBe(0);
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(3700);
    expect(ticks[1] - ticks[0]).toBe(1000);
  });

  it('regge un massimo a zero senza dividere per zero', () => {
    expect(niceTicks(0)).toEqual([0, 1]);
  });
});

describe('modalita di rendering', () => {
  it('sceglie lo standard in base allo spazio disponibile', () => {
    expect(resolveRenderMode(360)).toBe('compact');
    expect(resolveRenderMode(700)).toBe('standard');
    expect(resolveRenderMode(1200)).toBe('large');
  });

  it('accorcia le etichette invece di lasciarle tagliare dal contenitore', () => {
    expect(truncateToWidth('Contratto molto lungo', 11, 40)).toMatch(/…$/);
    expect(truncateToWidth('CTR-1', 11, 200)).toBe('CTR-1');
  });
});

describe('geometria delle barre', () => {
  it('tiene la larghezza minima dell area barre anche in poco spazio', () => {
    const layout = barLayout(rows([100, 200]), 200, BAR_SIZING.standard);

    // Sborda lo spazio disponibile invece di comprimersi: il contenitore scorre.
    expect(layout.width).toBeGreaterThan(200);
  });

  it('cresce in altezza con le righe, senza un tetto da scorrere a parte', () => {
    const poche = barLayout(rows([1, 2]), 900, BAR_SIZING.standard);
    const tante = barLayout(rows(Array.from({ length: 20 }, (_, index) => index + 1)), 900, BAR_SIZING.standard);

    expect(tante.height).toBeGreaterThan(poche.height);
    expect(tante.plotHeight).toBe(20 * BAR_SIZING.standard.rowHeight);
  });

  it('alza righe e testo nella modalita grande', () => {
    const molte = rows(Array.from({ length: 8 }, (_, index) => index + 1));
    const compact = barLayout(molte, 900, BAR_SIZING.compact);
    const large = barLayout(molte, 900, BAR_SIZING.large);

    expect(large.height).toBeGreaterThan(compact.height);
    expect(large.fontSize).toBeGreaterThan(compact.fontSize);
  });

  it('non lascia mai la barra spessa quanto la sua banda', () => {
    const poche = barLayout(rows([1, 2]), 900, BAR_SIZING.large);

    expect(poche.barHeight).toBeLessThanOrEqual(BAR_SIZING.large.maxBarThickness);
  });

  it('arrotonda solo l estremita del dato, non l attacco alla base', () => {
    const path = barPath(100, 20, 4);

    // Parte dall'origine squadrata e curva solo in fondo.
    expect(path.startsWith('M0,0')).toBe(true);
    expect(path).toContain('A4,4');
  });

  it('degrada a un rettangolo quando non c e spazio per la curva', () => {
    expect(barPath(0, 20)).toBe('M0,0 H0 V20 H0 Z');
  });
});
