import { describe, expect, it } from 'vitest';
import { render } from 'vitest-browser-svelte';
import CardGridHarness from './__fixtures__/CardGridHarness.svelte';

const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => resolve(null)));

function barCount() {
  return document.querySelectorAll('.card-overlay .row, .grid .chart-card:not(.placeholder) .row').length;
}

describe('ChartCard a schermo intero', () => {
  it('richiudendo, le altre card della griglia restano al loro posto', async () => {
    const screen = render(CardGridHarness);

    await screen.getByRole('button', { name: 'Apri a schermo intero: Classifica' }).click();
    expect(document.querySelector('.card-overlay')).not.toBeNull();

    await screen.getByRole('button', { name: 'Riduci il grafico' }).click();
    await nextFrame();

    expect(document.querySelector('.card-overlay')).toBeNull();
    await expect.element(screen.getByTestId('second')).toBeInTheDocument();
    await expect.element(screen.getByTestId('third')).toBeInTheDocument();
    expect(document.querySelectorAll('.grid .chart-card')).toHaveLength(3);
  });

  it('mostra 12 voci nella card e ne carica altre scorrendo a schermo intero', async () => {
    const screen = render(CardGridHarness);
    expect(barCount()).toBe(12);

    await screen.getByRole('button', { name: 'Apri a schermo intero: Classifica' }).click();
    await nextFrame();
    const body = document.querySelector<HTMLElement>('.card-overlay .chart-body')!;

    // Il corpo scorre dentro lo schermo invece di allungare la card oltre la finestra.
    expect(body.scrollHeight).toBeGreaterThan(body.clientHeight);
    expect(body.getBoundingClientRect().bottom).toBeLessThanOrEqual(window.innerHeight);
    const before = barCount();
    expect(before).toBeGreaterThanOrEqual(30);
    expect(before).toBeLessThan(120);

    body.scrollTop = body.scrollHeight;
    body.dispatchEvent(new Event('scroll'));
    await nextFrame();
    await nextFrame();
    expect(barCount()).toBeGreaterThan(before);

    await screen.getByRole('button', { name: 'mostra tutte' }).click();
    await nextFrame();
    expect(barCount()).toBe(120);
  });
});
